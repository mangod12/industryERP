<?php

namespace App\Models\Quality;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class QualityCause extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['code',  'label'];
}
