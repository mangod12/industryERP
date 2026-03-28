<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class ScrapRecord extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'material_name',
        'weight_kg',
        'length_mm',
        'width_mm',
        'thickness_mm',
        'quantity',
        'reason_code',
        'stage',
        'dimensions',
        'location',
        'notes',
        'status',
        'scrap_value',
        'work_order_id',
        'customer_id',
        'created_by',
        'processed_by',
        'processed_at',
    ];

    protected $casts = [
        'weight_kg' => 'decimal:2',
        'length_mm' => 'decimal:2',
        'width_mm' => 'decimal:2',
        'thickness_mm' => 'decimal:2',
        'scrap_value' => 'decimal:2',
        'processed_at' => 'datetime',
    ];

    /**
     * Get the reason code label from config
     */
    public function getReasonLabelAttribute(): string
    {
        return config("steel.scrap.reason_codes.{$this->reason_code}", ucfirst(str_replace('_', ' ', $this->reason_code)));
    }

    /**
     * Get the status label from config
     */
    public function getStatusLabelAttribute(): string
    {
        return config("steel.scrap.statuses.{$this->status}", ucfirst(str_replace('_', ' ', $this->status)));
    }

    /**
     * Created by user relationship
     */
    public function createdBy(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    /**
     * Processed by user relationship
     */
    public function processedBy(): BelongsTo
    {
        return $this->belongsTo(User::class, 'processed_by');
    }

    /**
     * Scope for pending scrap
     */
    public function scopePending($query)
    {
        return $query->where('status', 'pending');
    }

    /**
     * Scope for specific material
     */
    public function scopeByMaterial($query, string $material)
    {
        return $query->where('material_name', $material);
    }

    /**
     * Scope for specific reason
     */
    public function scopeByReason($query, string $reason)
    {
        return $query->where('reason_code', $reason);
    }

    /**
     * Mark as returned to inventory
     */
    public function returnToInventory(int $userId): bool
    {
        $this->status = 'returned_to_inventory';
        $this->processed_by = $userId;
        $this->processed_at = now();
        return $this->save();
    }

    /**
     * Move to reusable stock
     */
    public function moveToReusable(int $userId, string $qualityGrade = 'B'): ReusableStock
    {
        $reusable = ReusableStock::create([
            'material_name' => $this->material_name,
            'weight_kg' => $this->weight_kg,
            'length_mm' => $this->length_mm,
            'width_mm' => $this->width_mm,
            'thickness_mm' => $this->thickness_mm,
            'quantity' => $this->quantity,
            'dimensions' => $this->dimensions,
            'quality_grade' => $qualityGrade,
            'location' => $this->location,
            'notes' => $this->notes,
            'scrap_record_id' => $this->id,
            'status' => 'available',
            'created_by' => $userId,
        ]);

        $this->status = 'moved_to_reusable';
        $this->processed_by = $userId;
        $this->processed_at = now();
        $this->save();

        return $reusable;
    }

    /**
     * Mark as disposed
     */
    public function dispose(int $userId): bool
    {
        $this->status = 'disposed';
        $this->processed_by = $userId;
        $this->processed_at = now();
        return $this->save();
    }

    /**
     * Mark as sold
     */
    public function sell(int $userId, float $value): bool
    {
        $this->status = 'sold';
        $this->scrap_value = $value;
        $this->processed_by = $userId;
        $this->processed_at = now();
        return $this->save();
    }
}
