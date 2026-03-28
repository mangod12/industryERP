<?php

namespace App\Http\Controllers;

use App\Models\ScrapRecord;
use App\Models\ReusableStock;
use App\Exports\ScrapRecordsExport;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Maatwebsite\Excel\Facades\Excel;

class ScrapController extends Controller
{
    /**
     * Display the scrap inventory listing
     */
    public function index(Request $request)
    {
        $query = ScrapRecord::with(['customer', 'createdBy', 'processedBy']);

        // Filters
        if ($request->filled('material')) {
            $query->byMaterial($request->material);
        }
        if ($request->filled('status')) {
            $query->where('status', $request->status);
        }
        if ($request->filled('reason')) {
            $query->byReason($request->reason);
        }
        if ($request->filled('date_from')) {
            $query->whereDate('created_at', '>=', $request->date_from);
        }
        if ($request->filled('date_to')) {
            $query->whereDate('created_at', '<=', $request->date_to);
        }

        $scrapRecords = $query->orderBy('created_at', 'desc')->paginate(25);

        // Statistics
        $stats = [
            'total_weight' => ScrapRecord::sum('weight_kg'),
            'pending_weight' => ScrapRecord::pending()->sum('weight_kg'),
            'pending_count' => ScrapRecord::pending()->count(),
            'scrap_value' => ScrapRecord::where('status', 'sold')->sum('scrap_value'),
        ];

        // Get unique materials and reasons for filters
        $materials = ScrapRecord::distinct()->pluck('material_name');
        $reasonCodes = config('steel.scrap.reason_codes', [
            'cutting_waste' => 'Cutting Waste',
            'defect' => 'Manufacturing Defect',
            'damage' => 'Handling Damage',
            'overrun' => 'Production Overrun',
            'leftover' => 'Leftover Material',
        ]);
        $statuses = config('steel.scrap.statuses', [
            'pending' => 'Pending Review',
            'returned_to_inventory' => 'Returned to Inventory',
            'moved_to_reusable' => 'Moved to Reusable',
            'disposed' => 'Disposed',
            'sold' => 'Sold as Scrap',
        ]);

        return view('scrap.index', compact(
            'scrapRecords', 'stats', 'materials', 'reasonCodes', 'statuses'
        ));
    }

    /**
     * Show form for creating new scrap record
     */
    public function create()
    {
        $materials = config('steel.material_types');
        $reasonCodes = config('steel.scrap.reason_codes');
        
        return view('scrap.create', compact('materials', 'reasonCodes'));
    }

    /**
     * Store a new scrap record
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'material_name' => 'required|string|max:255',
            'weight_kg' => 'required|numeric|min:0.01',
            'length_mm' => 'nullable|numeric|min:0',
            'width_mm' => 'nullable|numeric|min:0',
            'thickness_mm' => 'nullable|numeric|min:0',
            'quantity' => 'required|integer|min:1',
            'reason_code' => 'required|string',
            'dimensions' => 'nullable|string|max:500',
            'notes' => 'nullable|string',
            'source_order_id' => 'nullable|exists:orders,id',
            'customer_id' => 'nullable|exists:companies,id',
        ]);

        $validated['created_by'] = auth()->id();
        $validated['status'] = 'pending';

        $scrap = ScrapRecord::create($validated);

        return redirect()->route('scrap.index')
            ->with('success', 'Scrap record created successfully.');
    }

    /**
     * Show CSV upload form
     */
    public function uploadForm()
    {
        $reasonCodes = config('steel.scrap.reason_codes');
        return view('scrap.upload', compact('reasonCodes'));
    }

    /**
     * Process CSV upload
     */
    public function upload(Request $request)
    {
        $request->validate([
            'csv_file' => 'required|file|mimes:csv,txt|max:10240',
            'default_reason' => 'required|string',
            'source_order_id' => 'nullable|exists:orders,id',
            'customer_id' => 'nullable|exists:companies,id',
        ]);

        $file = $request->file('csv_file');
        $records = [];
        $errors = [];

        if (($handle = fopen($file->getRealPath(), 'r')) !== false) {
            $header = fgetcsv($handle);
            $header = array_map('strtolower', array_map('trim', $header));
            
            $rowNum = 1;
            while (($data = fgetcsv($handle)) !== false) {
                $rowNum++;
                $row = array_combine($header, $data);
                
                try {
                    $records[] = [
                        'material_name' => $row['material'] ?? $row['material_name'] ?? 'Unknown',
                        'weight_kg' => floatval($row['weight'] ?? $row['weight_kg'] ?? 0),
                        'length_mm' => floatval($row['length'] ?? $row['length_mm'] ?? null),
                        'width_mm' => floatval($row['width'] ?? $row['width_mm'] ?? null),
                        'thickness_mm' => floatval($row['thickness'] ?? $row['thickness_mm'] ?? null),
                        'quantity' => intval($row['qty'] ?? $row['quantity'] ?? 1),
                        'reason_code' => $row['reason'] ?? $request->default_reason,
                        'dimensions' => $row['dimensions'] ?? null,
                        'notes' => $row['notes'] ?? null,
                        'source_order_id' => $request->source_order_id,
                        'customer_id' => $request->customer_id,
                        'created_by' => auth()->id(),
                        'status' => 'pending',
                        'created_at' => now(),
                        'updated_at' => now(),
                    ];
                } catch (\Exception $e) {
                    $errors[] = "Row {$rowNum}: " . $e->getMessage();
                }
            }
            fclose($handle);
        }

        if (count($records) > 0) {
            ScrapRecord::insert($records);
        }

        $message = count($records) . ' scrap records imported successfully.';
        if (count($errors) > 0) {
            $message .= ' ' . count($errors) . ' rows had errors.';
        }

        return redirect()->route('scrap.index')
            ->with('success', $message)
            ->with('errors', $errors);
    }

    /**
     * Show single scrap record
     */
    public function show(ScrapRecord $scrap)
    {
        $scrap->load(['customer', 'sourceOrder', 'createdBy', 'processedBy']);
        return view('scrap.show', compact('scrap'));
    }

    /**
     * Process scrap action (return, reusable, dispose, sell)
     */
    public function processAction(Request $request, ScrapRecord $scrap)
    {
        $request->validate([
            'action' => 'required|in:return,reusable,dispose,recycle,sell',
            'quality_grade' => 'required_if:action,reusable|in:A,B,C',
            'scrap_value' => 'required_if:action,sell|numeric|min:0',
        ]);

        $userId = auth()->id();

        switch ($request->action) {
            case 'return':
                $scrap->returnToInventory($userId);
                $message = 'Material returned to inventory.';
                break;

            case 'reusable':
                $scrap->moveToReusable($userId, $request->quality_grade ?? 'A');
                $message = 'Material moved to reusable stock.';
                break;

            case 'dispose':
                $scrap->dispose($userId);
                $message = 'Scrap marked as disposed.';
                break;

            case 'recycle':
                $scrap->status = 'recycled';
                $scrap->processed_by = $userId;
                $scrap->processed_at = now();
                $scrap->save();
                $message = 'Scrap marked for recycling.';
                break;

            case 'sell':
                $scrap->sell($userId, $request->scrap_value);
                $message = 'Scrap marked as sold.';
                break;
        }

        return redirect()->back()->with('success', $message);
    }

    /**
     * Bulk action on multiple scrap records
     */
    public function bulkAction(Request $request)
    {
        $request->validate([
            'ids' => 'required|array',
            'ids.*' => 'exists:scrap_records,id',
            'action' => 'required|in:return,dispose,recycle',
        ]);

        $userId = auth()->id();
        $count = 0;

        foreach ($request->ids as $id) {
            $scrap = ScrapRecord::find($id);
            if ($scrap && $scrap->status === 'pending') {
                switch ($request->action) {
                    case 'return':
                        $scrap->returnToInventory($userId);
                        break;
                    case 'dispose':
                        $scrap->dispose($userId);
                        break;
                    case 'recycle':
                        $scrap->status = 'recycled';
                        $scrap->processed_by = $userId;
                        $scrap->processed_at = now();
                        $scrap->save();
                        break;
                }
                $count++;
            }
        }

        return redirect()->back()->with('success', "{$count} records processed successfully.");
    }

    /**
     * Get analytics data
     */
    public function analytics(Request $request)
    {
        $period = $request->get('period', 'month');
        
        switch ($period) {
            case 'week':
                $startDate = now()->subWeek();
                break;
            case 'quarter':
                $startDate = now()->subMonths(3);
                break;
            case 'year':
                $startDate = now()->subYear();
                break;
            default:
                $startDate = now()->subMonth();
        }

        // Scrap by reason
        $byReason = ScrapRecord::where('created_at', '>=', $startDate)
            ->select('reason_code', DB::raw('SUM(weight_kg) as total_weight'), DB::raw('COUNT(*) as count'))
            ->groupBy('reason_code')
            ->orderBy('total_weight', 'desc')
            ->get();

        // Scrap by material
        $byMaterial = ScrapRecord::where('created_at', '>=', $startDate)
            ->select('material_name', DB::raw('SUM(weight_kg) as total_weight'), DB::raw('COUNT(*) as count'))
            ->groupBy('material_name')
            ->orderBy('total_weight', 'desc')
            ->limit(10)
            ->get();

        // Scrap by stage
        $byStage = ScrapRecord::where('created_at', '>=', $startDate)
            ->whereNotNull('stage')
            ->select('stage', DB::raw('SUM(weight_kg) as total_weight'), DB::raw('COUNT(*) as count'))
            ->groupBy('stage')
            ->orderBy('total_weight', 'desc')
            ->get();

        // Scrap by status
        $byStatus = ScrapRecord::where('created_at', '>=', $startDate)
            ->select('status', DB::raw('COUNT(*) as count'))
            ->groupBy('status')
            ->get();

        // Daily trend
        $trend = ScrapRecord::where('created_at', '>=', $startDate)
            ->select(DB::raw('DATE(created_at) as date'), DB::raw('SUM(weight_kg) as total_weight'))
            ->groupBy('date')
            ->orderBy('date')
            ->get();

        // Calculate totals
        $totalWeight = ScrapRecord::where('created_at', '>=', $startDate)->sum('weight_kg');
        $pendingCount = ScrapRecord::pending()->count();
        $valueRecovered = ScrapRecord::where('status', 'sold')
            ->where('created_at', '>=', $startDate)
            ->sum('scrap_value');
        
        // Recovery calculations
        $returnedWeight = ScrapRecord::whereIn('status', ['returned_to_inventory', 'moved_to_reusable', 'sold'])
            ->where('created_at', '>=', $startDate)
            ->sum('weight_kg');
        $recoveryRate = $totalWeight > 0 ? ($returnedWeight / $totalWeight) * 100 : 0;

        // Estimate scrap rate (would need actual production data for accuracy)
        $scrapRate = 3.5; // Placeholder - needs actual production tracking

        $data = [
            'total_weight' => $totalWeight,
            'scrap_rate' => $scrapRate,
            'value_recovered' => $valueRecovered,
            'recovery_rate' => $recoveryRate,
            'pending_count' => $pendingCount,
            'by_material' => $byMaterial,
            'by_reason' => $byReason,
            'by_stage' => $byStage,
            'by_status' => $byStatus,
            'trend' => $trend,
        ];

        return view('scrap.analytics', compact('data'));
    }

    /**
     * Export scrap records
     */
    public function export(Request $request)
    {
        return Excel::download(new ScrapRecordsExport($request->all()), 'scrap_records.xlsx');
    }
}
