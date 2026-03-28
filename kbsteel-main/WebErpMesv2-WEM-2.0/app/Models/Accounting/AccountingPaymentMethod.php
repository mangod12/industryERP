<?php

namespace App\Models\Accounting;

use App\Traits\HasDefaultTrait;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

/**
 * Class AccountingPaymentMethod
 *
 * This model represents a payment method in the accounting system.
 * It uses the HasFactory and HasDefaultTrait traits.
 *
 */
class AccountingPaymentMethod extends Model
{
    use HasFactory; use HasDefaultTrait;

     // Fillable attributes for mass assignment
    protected $fillable= ['code',  'label',  'code_account',  'default'];
}
