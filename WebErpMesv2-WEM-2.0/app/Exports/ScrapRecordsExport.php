<?php

namespace App\Exports;

use App\Models\ScrapRecord;
use Maatwebsite\Excel\Concerns\FromQuery;
use Maatwebsite\Excel\Concerns\WithHeadings;
use Maatwebsite\Excel\Concerns\WithMapping;
use Maatwebsite\Excel\Concerns\ShouldAutoSize;
use Maatwebsite\Excel\Concerns\WithStyles;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;

class ScrapRecordsExport implements FromQuery, WithHeadings, WithMapping, ShouldAutoSize, WithStyles
{
    protected $filters;

    public function __construct(array $filters = [])
    {
        $this->filters = $filters;
    }

    public function query()
    {
        $query = ScrapRecord::query()->with(['customer', 'createdBy']);

        if (!empty($this->filters['status'])) {
            $query->where('status', $this->filters['status']);
        }

        if (!empty($this->filters['material'])) {
            $query->where('material_name', $this->filters['material']);
        }

        if (!empty($this->filters['reason'])) {
            $query->where('reason_code', $this->filters['reason']);
        }

        if (!empty($this->filters['date_from'])) {
            $query->whereDate('created_at', '>=', $this->filters['date_from']);
        }

        if (!empty($this->filters['date_to'])) {
            $query->whereDate('created_at', '<=', $this->filters['date_to']);
        }

        return $query->orderBy('created_at', 'desc');
    }

    public function headings(): array
    {
        return [
            'ID',
            'Material Name',
            'Weight (kg)',
            'Quantity',
            'Length (mm)',
            'Width (mm)',
            'Thickness (mm)',
            'Dimensions',
            'Reason Code',
            'Reason',
            'Production Stage',
            'Status',
            'Location',
            'Scrap Value (₹)',
            'Customer',
            'Work Order',
            'Notes',
            'Created By',
            'Created At',
            'Processed At',
        ];
    }

    public function map($scrap): array
    {
        return [
            $scrap->id,
            $scrap->material_name,
            $scrap->weight_kg,
            $scrap->quantity,
            $scrap->length_mm,
            $scrap->width_mm,
            $scrap->thickness_mm,
            $scrap->dimensions,
            $scrap->reason_code,
            $scrap->reason_label,
            ucfirst($scrap->stage),
            ucfirst(str_replace('_', ' ', $scrap->status)),
            $scrap->location,
            $scrap->scrap_value,
            $scrap->customer?->name,
            $scrap->work_order_id,
            $scrap->notes,
            $scrap->createdBy?->name,
            $scrap->created_at->format('Y-m-d H:i:s'),
            $scrap->processed_at?->format('Y-m-d H:i:s'),
        ];
    }

    public function styles(Worksheet $sheet): array
    {
        return [
            1 => [
                'font' => ['bold' => true],
                'fill' => [
                    'fillType' => \PhpOffice\PhpSpreadsheet\Style\Fill::FILL_SOLID,
                    'startColor' => ['rgb' => 'FFC107']
                ]
            ],
        ];
    }
}
