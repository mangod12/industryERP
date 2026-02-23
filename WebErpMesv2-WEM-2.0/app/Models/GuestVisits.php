<?php

namespace App\Models;

use Carbon\Carbon;
use App\Models\Workflow\Quotes;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class GuestVisits extends Model
{
    use HasFactory;

    /**
     * Les attributs qui sont mass assignable.
     *
     * @var array
     */
    // Fillable attributes for mass assignment
    protected $fillable= [
        'ip_address',
        'url_visited',
        'visit_type',
        'quotes_id',
        'visited_at',
    ];

    /**
     * Récupère le devis associé à cette visite.
     */
    public function quote()
    {
        return $this->belongsTo(Quotes::class, 'quotes_id');
    }

    /**
     * Get the formatted creation date of the line.
     *
     * This accessor method returns the creation date of line
     * formatted as 'day month year' (e.g., '01 January 2023').
     *
     * @return string The formatted creation date.
     */
    public function GetPrettyCreatedAttribute()
    {
        return Carbon::parse($this->visited_at)->diffForHumans();
    }
}
