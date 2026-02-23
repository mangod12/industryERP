<?php

namespace App\Models\Accounting;

use Illuminate\Database\Eloquent\Model;
use App\Models\Accounting\AccountingVat;
use Illuminate\Database\Eloquent\Factories\HasFactory;

/**
 * Class AccountingAllocation
 * 
 * This class represents an accounting allocation model.
 * It uses the HasFactory trait and defines fillable attributes.
 * It also defines a relationship with the AccountingVat model.
 */
class AccountingAllocation extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['account',  'label',  'accounting_vats_id',  'vat_account',  'code_account',  'type_imputation'];

    /**
     * Define a relationship with the AccountingVat model.
     * 
     * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
     */
    public function VAT()
    {
        return $this->belongsTo(AccountingVat::class, 'accounting_vats_id');
    }
}
