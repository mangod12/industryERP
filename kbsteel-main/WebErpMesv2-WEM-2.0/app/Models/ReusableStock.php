<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Builder;

class ReusableStock extends Model
{
    use HasFactory, SoftDeletes;

    protected $table = 'reusable_stock';

    protected $fillable = [
        'material_name',
        'weight_kg',
        'length_mm',
        'width_mm',
        'thickness_mm',
        'quantity',
        'dimensions',
        'quality_grade',
        'notes',
        'status',
        'location',
        'scrap_record_id',
        'used_at',
        'used_by',
        'used_for_work_order',
        'returned_at',
        'returned_by',
        'created_by',
    ];

    protected $casts = [
        'weight_kg' => 'decimal:2',
        'length_mm' => 'decimal:2',
        'width_mm' => 'decimal:2',
        'thickness_mm' => 'decimal:2',
        'used_at' => 'datetime',
        'returned_at' => 'datetime',
    ];

    /**
     * Get the quality grade label from config
     */
    public function getQualityLabelAttribute(): string
    {
        return config("steel.reusable.quality_grades.{$this->quality_grade}", $this->quality_grade);
    }

    /**
     * Source scrap record relationship
     */
    public function scrapRecord(): BelongsTo
    {
        return $this->belongsTo(ScrapRecord::class, 'scrap_record_id');
    }

    /**
     * Created by user relationship
     */
    public function createdBy(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    /**
     * Used by user relationship
     */
    public function usedBy(): BelongsTo
    {
        return $this->belongsTo(User::class, 'used_by');
    }

    /**
     * Scope for available stock only
     */
    public function scopeAvailable(Builder $query): Builder
    {
        return $query->where('status', 'available');
    }

    /**
     * Scope for specific material
     */
    public function scopeByMaterial(Builder $query, string $material): Builder
    {
        return $query->where('material_name', $material);
    }

    /**
     * Scope for minimum quality grade
     */
    public function scopeMinGrade(Builder $query, string $grade): Builder
    {
        $grades = ['A' => 1, 'B' => 2, 'C' => 3];
        $minGrade = $grades[$grade] ?? 3;
        
        return $query->whereIn('quality_grade', array_keys(array_filter($grades, fn($v) => $v <= $minGrade)));
    }

    /**
     * Find matching pieces for a required dimension with tolerance
     */
    public function scopeFindMatch(
        Builder $query, 
        string $material, 
        ?float $minLength = null, 
        ?float $minWidth = null, 
        ?float $thickness = null
    ): Builder {
        $tolerance = config('steel.reusable.match_tolerance_mm', 10);

        $query->available()->byMaterial($material);

        if ($minLength) {
            $query->where('length_mm', '>=', $minLength);
        }

        if ($minWidth) {
            $query->where('width_mm', '>=', $minWidth);
        }

        if ($thickness) {
            $query->whereBetween('thickness_mm', [$thickness - $tolerance, $thickness + $tolerance]);
        }

        return $query->orderBy('weight_kg', 'asc'); // Prefer smaller pieces first
    }

    /**
     * Mark as used in an order
     */
    public function markAsUsed(int $orderId, ?int $orderLineId = null): bool
    {
        $this->is_available = false;
        $this->used_in_order_id = $orderId;
        $this->used_in_order_line_id = $orderLineId;
        $this->used_at = now();
        return $this->save();
    }

    /**
     * Return to available stock
     */
    public function returnToAvailable(): bool
    {
        $this->is_available = true;
        $this->used_in_order_id = null;
        $this->used_in_order_line_id = null;
        $this->used_at = null;
        return $this->save();
    }

    /**
     * Convert back to scrap (mark as waste)
     */
    public function markAsScrap(int $userId, string $reason = 'defect'): ScrapRecord
    {
        $scrap = ScrapRecord::create([
            'material_name' => $this->material_name,
            'weight_kg' => $this->weight_kg,
            'length_mm' => $this->length_mm,
            'width_mm' => $this->width_mm,
            'thickness_mm' => $this->thickness_mm,
            'quantity' => $this->quantity,
            'dimensions' => $this->dimensions,
            'reason_code' => $reason,
            'notes' => "Converted from reusable stock #{$this->id}. " . $this->notes,
            'status' => 'pending',
            'source_order_id' => $this->source_order_id,
            'customer_id' => $this->customer_id,
            'created_by' => $userId,
        ]);

        $this->delete(); // Soft delete

        return $scrap;
    }

    /**
     * Return to main inventory
     */
    public function returnToInventory(int $userId): bool
    {
        // This would integrate with the Products/Stocks model to add back to inventory
        // For now, just mark as used and add a note
        $this->notes = ($this->notes ? $this->notes . "\n" : '') . "Returned to main inventory by user #{$userId} at " . now();
        $this->is_available = false;
        return $this->save();
    }
}
