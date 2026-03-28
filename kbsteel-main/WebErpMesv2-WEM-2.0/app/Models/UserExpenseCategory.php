<?php

namespace App\Models;

use App\Models\UserExpense;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class UserExpenseCategory extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['label', 'description'];

    /**
     * Get the expenses associated with the user expense category.
     *
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function expenses()
    {
        return $this->hasMany(UserExpense::class, 'category_id');
    }
}
