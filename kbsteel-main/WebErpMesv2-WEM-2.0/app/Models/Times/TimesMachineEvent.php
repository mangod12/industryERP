<?php

namespace App\Models\Times;

use Illuminate\Database\Eloquent\Model;
use App\Models\Times\TimesImproductTime;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class TimesMachineEvent extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['code',  'ordre',  'label',  'mask_time',  'color',  'etat'];

    public function improductTime()
    {
        return $this->hasMany(TimesImproductTime::class);
    }

}
