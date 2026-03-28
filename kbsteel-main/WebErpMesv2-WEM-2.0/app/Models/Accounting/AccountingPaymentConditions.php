<?php

namespace App\Models\Accounting;

use App\Traits\HasDefaultTrait;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

/**
 * Class AccountingPaymentConditions
 *
 * This model represents the payment conditions in the accounting system.
 * It uses the HasFactory and HasDefaultTrait traits.
 *
 */
class AccountingPaymentConditions extends Model
{
    use HasFactory; use HasDefaultTrait;

    // Fillable attributes for mass assignment
    protected $fillable= ['code',  'label',  'number_of_month',  'number_of_day',  'month_end',  'default'];
}
