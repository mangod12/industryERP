<?php

namespace App\Models\Quality;

use Illuminate\Database\Eloquent\Model;
use App\Models\Quality\QualityNonConformity;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class QualityFailure extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['code',  'label'];

    public function QualityNonConformity()
    {
        return $this->hasMany(QualityNonConformity::class);
    }
}
