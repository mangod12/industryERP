<?php

namespace App\Http\Controllers;

use App\Models\ReusableStock;
use App\Models\ScrapRecord;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ReusableStockController extends Controller
{
    /**
     * Display reusable stock listing
     */
    public function index(Request $request)
    {
        $query = ReusableStock::query();

        // Filters
        if ($request->filled('material')) {
            $query->where('material_name', $request->material);
        }
        if ($request->filled('status')) {
            if ($request->status === 'available') {
                $query->available();
            } elseif ($request->status === 'reserved') {
                $query->where('status', 'reserved');
            } elseif ($request->status === 'used') {
                $query->whereNotNull('used_at');
            }
        }
        if ($request->filled('grade')) {
            $query->where('quality_grade', $request->grade);
        }
        if ($request->filled('min_length')) {
            $query->where('length_mm', '>=', $request->min_length);
        }
        if ($request->filled('min_width')) {
            $query->where('width_mm', '>=', $request->min_width);
        }

        $reusableStock = $query->orderBy('created_at', 'desc')->paginate(25);

        // Statistics
        $stats = [
            'available_weight' => ReusableStock::available()->sum('weight_kg'),
            'available_count' => ReusableStock::available()->count(),
            'used_weight' => ReusableStock::whereNotNull('used_at')
                ->whereMonth('used_at', now()->month)
                ->sum('weight_kg'),
            'estimated_value' => ReusableStock::available()->sum('weight_kg') * 0.6 * 80, // 60% of material cost
        ];

        // Get unique materials for filter
        $materials = ReusableStock::distinct()->pluck('material_name');

        return view('reusable.index', compact(
            'reusableStock', 'stats', 'materials'
        ));
    }

    /**
     * Show form for creating reusable stock entry
     */
    public function create()
    {
        $materials = config('steel.material_types');
        $qualityGrades = config('steel.reusable.quality_grades');
        
        return view('reusable.create', compact('materials', 'qualityGrades'));
    }

    /**
     * Store a new reusable stock entry
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'material_name' => 'required|string|max:255',
            'weight_kg' => 'required|numeric|min:0.01',
            'length_mm' => 'required|numeric|min:1',
            'width_mm' => 'required|numeric|min:1',
            'thickness_mm' => 'nullable|numeric|min:0',
            'quantity' => 'nullable|integer|min:1',
            'quality_grade' => 'required|in:A,B,C',
            'location' => 'nullable|string|max:255',
            'notes' => 'nullable|string',
            'scrap_record_id' => 'nullable|exists:scrap_records,id',
        ]);

        $validated['created_by'] = auth()->id();
        $validated['status'] = 'available';
        $validated['quantity'] = $validated['quantity'] ?? 1;

        $reusable = ReusableStock::create($validated);

        return redirect()->route('reusable.index')
            ->with('success', 'Reusable stock entry created successfully.');
    }

    /**
     * Show single reusable stock entry
     */
    public function show(ReusableStock $item)
    {
        $item->load(['scrapRecord']);
        
        // Find similar items
        $similarItems = ReusableStock::available()
            ->where('id', '!=', $item->id)
            ->where('material_name', $item->material_name)
            ->limit(5)
            ->get();
            
        return view('reusable.show', compact('item', 'similarItems'));
    }

    /**
     * Find matching reusable pieces for a requirement
     */
    public function findMatch(Request $request)
    {
        $matches = null;
        $availableCount = ReusableStock::available()->count();
        $gradeACount = ReusableStock::available()->where('quality_grade', 'A')->count();
        $totalWeight = ReusableStock::available()->sum('weight_kg');

        if ($request->filled('material') && $request->filled('min_length') && $request->filled('min_width')) {
            $query = ReusableStock::available()
                ->where('material_name', $request->material)
                ->where('length_mm', '>=', $request->min_length)
                ->where('width_mm', '>=', $request->min_width);

            if ($request->filled('thickness')) {
                $query->where('thickness_mm', $request->thickness);
            }

            if ($request->filled('min_grade')) {
                $gradeOrder = ['A' => 1, 'B' => 2, 'C' => 3];
                $minGradeOrder = $gradeOrder[$request->min_grade] ?? 3;
                $acceptableGrades = array_filter($gradeOrder, fn($order) => $order <= $minGradeOrder);
                $query->whereIn('quality_grade', array_keys($acceptableGrades));
            }

            // Order by closest match (smallest excess first), then by grade
            $matches = $query->orderByRaw('(length_mm - ?) + (width_mm - ?)', [$request->min_length, $request->min_width])
                ->orderByRaw("FIELD(quality_grade, 'A', 'B', 'C')")
                ->limit(20)
                ->get();
        }

        return view('reusable.find-match', compact('matches', 'availableCount', 'gradeACount', 'totalWeight'));
    }

    /**
     * Mark reusable stock as used in production
     */
    public function markUsed(Request $request, ReusableStock $item)
    {
        if ($item->status !== 'available') {
            return redirect()->back()->with('error', 'This stock is no longer available.');
        }

        $item->status = 'used';
        $item->used_at = now();
        $item->used_by = auth()->id();
        $item->used_for_work_order = $request->work_order_id;
        $item->save();

        return redirect()->back()->with('success', 'Stock marked as used.');
    }

    /**
     * Return reusable stock to available
     */
    public function returnToAvailable(ReusableStock $item)
    {
        $item->status = 'available';
        $item->used_at = null;
        $item->used_by = null;
        $item->used_for_work_order = null;
        $item->save();
        
        return redirect()->back()->with('success', 'Stock returned to available.');
    }

    /**
     * Return to main inventory
     */
    public function returnToInventory(ReusableStock $item)
    {
        // In a real implementation, this would add to main inventory
        $item->status = 'returned';
        $item->returned_at = now();
        $item->returned_by = auth()->id();
        $item->save();
        
        return redirect()->route('reusable.index')
            ->with('success', 'Stock returned to main inventory.');
    }

    /**
     * Convert back to scrap
     */
    public function markAsScrap(Request $request, ReusableStock $item)
    {
        // Create a new scrap record from this reusable item
        ScrapRecord::create([
            'material_name' => $item->material_name,
            'weight_kg' => $item->weight_kg,
            'length_mm' => $item->length_mm,
            'width_mm' => $item->width_mm,
            'thickness_mm' => $item->thickness_mm,
            'quantity' => $item->quantity,
            'reason_code' => 'defect',
            'status' => 'pending',
            'notes' => 'Returned from reusable stock #' . $item->id,
            'created_by' => auth()->id(),
        ]);
        
        $item->status = 'scrapped';
        $item->save();
        
        return redirect()->route('scrap.index')
            ->with('success', 'Stock converted to scrap record.');
    }

    /**
     * Update quality grade
     */
    public function updateGrade(Request $request, ReusableStock $item)
    {
        $request->validate([
            'quality_grade' => 'required|in:A,B,C',
        ]);

        $item->quality_grade = $request->quality_grade;
        $item->save();

        return redirect()->back()->with('success', 'Quality grade updated.');
    }

    /**
     * Bulk action on multiple reusable stock items
     */
    public function bulkAction(Request $request)
    {
        $request->validate([
            'ids' => 'required|array',
            'ids.*' => 'exists:reusable_stock,id',
            'action' => 'required|in:scrap,return',
        ]);

        $userId = auth()->id();
        $count = 0;

        foreach ($request->ids as $id) {
            $item = ReusableStock::find($id);
            if ($item && $item->status === 'available') {
                switch ($request->action) {
                    case 'scrap':
                        ScrapRecord::create([
                            'material_name' => $item->material_name,
                            'weight_kg' => $item->weight_kg,
                            'length_mm' => $item->length_mm,
                            'width_mm' => $item->width_mm,
                            'thickness_mm' => $item->thickness_mm,
                            'quantity' => $item->quantity,
                            'reason_code' => 'defect',
                            'status' => 'pending',
                            'notes' => 'Bulk returned from reusable stock',
                            'created_by' => $userId,
                        ]);
                        $item->status = 'scrapped';
                        $item->save();
                        break;
                    case 'return':
                        $item->status = 'returned';
                        $item->returned_at = now();
                        $item->returned_by = $userId;
                        $item->save();
                        break;
                }
                $count++;
            }
        }

        return redirect()->back()->with('success', "{$count} items processed successfully.");
    }

    /**
     * Get analytics/summary
     */
    public function analytics()
    {
        // By material
        $byMaterial = ReusableStock::available()
            ->select('material_name', DB::raw('COUNT(*) as count'), DB::raw('SUM(weight_kg) as total_weight'))
            ->groupBy('material_name')
            ->orderBy('total_weight', 'desc')
            ->get();

        // By grade
        $byGradeRaw = ReusableStock::available()
            ->select('quality_grade', DB::raw('COUNT(*) as count'), DB::raw('SUM(weight_kg) as total_weight'))
            ->groupBy('quality_grade')
            ->get();
        
        $byGrade = [
            'A' => $byGradeRaw->where('quality_grade', 'A')->first()?->count ?? 0,
            'B' => $byGradeRaw->where('quality_grade', 'B')->first()?->count ?? 0,
            'C' => $byGradeRaw->where('quality_grade', 'C')->first()?->count ?? 0,
        ];

        // By status
        $byStatus = [
            'available' => ReusableStock::available()->count(),
            'reserved' => ReusableStock::where('status', 'reserved')->count(),
            'used' => ReusableStock::whereNotNull('used_at')->count(),
        ];

        // Age analysis
        $aging = [
            [
                'label' => '< 30 days',
                'days' => 15,
                'count' => ReusableStock::available()->where('created_at', '>=', now()->subDays(30))->count(),
                'weight' => ReusableStock::available()->where('created_at', '>=', now()->subDays(30))->sum('weight_kg'),
            ],
            [
                'label' => '30-90 days',
                'days' => 60,
                'count' => ReusableStock::available()
                    ->where('created_at', '<', now()->subDays(30))
                    ->where('created_at', '>=', now()->subDays(90))
                    ->count(),
                'weight' => ReusableStock::available()
                    ->where('created_at', '<', now()->subDays(30))
                    ->where('created_at', '>=', now()->subDays(90))
                    ->sum('weight_kg'),
            ],
            [
                'label' => '> 90 days',
                'days' => 120,
                'count' => ReusableStock::available()->where('created_at', '<', now()->subDays(90))->count(),
                'weight' => ReusableStock::available()->where('created_at', '<', now()->subDays(90))->sum('weight_kg'),
            ],
        ];

        // Trend - monthly added vs used
        $trend = collect();
        for ($i = 5; $i >= 0; $i--) {
            $monthStart = now()->subMonths($i)->startOfMonth();
            $monthEnd = now()->subMonths($i)->endOfMonth();
            
            $trend->push([
                'date' => $monthStart->format('M Y'),
                'added' => ReusableStock::whereBetween('created_at', [$monthStart, $monthEnd])->sum('weight_kg'),
                'used' => ReusableStock::whereNotNull('used_at')->whereBetween('used_at', [$monthStart, $monthEnd])->sum('weight_kg'),
            ]);
        }

        // Summary stats
        $availableWeight = ReusableStock::available()->sum('weight_kg');
        $availableCount = ReusableStock::available()->count();
        $usedThisMonth = ReusableStock::whereNotNull('used_at')
            ->whereMonth('used_at', now()->month)
            ->sum('weight_kg');
        $totalEverAdded = ReusableStock::sum('weight_kg');
        $totalEverUsed = ReusableStock::whereNotNull('used_at')->sum('weight_kg');
        
        // Calculate average age
        $avgAgeDays = ReusableStock::available()
            ->selectRaw('AVG(DATEDIFF(NOW(), created_at)) as avg_days')
            ->value('avg_days') ?? 0;

        // Value saved (estimated at 60% of new material cost, ~80/kg for MS)
        $valueSaved = $totalEverUsed * 0.6 * 80;

        $data = [
            'available_weight' => $availableWeight,
            'available_count' => $availableCount,
            'utilization_rate' => $totalEverAdded > 0 ? ($totalEverUsed / $totalEverAdded) * 100 : 0,
            'avg_age_days' => $avgAgeDays,
            'value_saved' => $valueSaved,
            'by_material' => $byMaterial,
            'by_grade' => $byGrade,
            'by_status' => $byStatus,
            'aging' => $aging,
            'trend' => $trend,
        ];

        return view('reusable.analytics', compact('data'));
    }
}
