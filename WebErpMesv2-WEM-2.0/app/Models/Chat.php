<?php

namespace App\Models;

use Carbon\Carbon;
use App\Models\User;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Chat extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['label','user_id','related_id','related_type'];

    public function User()
    {
        return $this->belongsTo(User::class, 'user_id');
    }

    /**
     * Get the formatted creation date of the chat.
     *
     * This accessor method returns the creation date of the chat
     * formatted as 'day month year' (e.g., '01 January 2023').
     *
     * @return string The formatted creation date.
     */
    public function GetPrettyCreatedAttribute()
    {
        return Carbon::parse($this->created_at)->diffForHumans();
    }
}
