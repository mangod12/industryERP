<?php

namespace App\Models\Accounting;

use App\Traits\HasDefaultTrait;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

/**
 * Class AccountingDelivery
 * 
 * This class represents the AccountingDelivery model.
 * It uses the HasFactory and HasDefaultTrait traits.
 */
class AccountingDelivery extends Model
{
    use HasFactory; 
    use HasDefaultTrait;

    // Fillable attributes for mass assignment
    protected $fillable= ['code', 'label', 'default'];
}
