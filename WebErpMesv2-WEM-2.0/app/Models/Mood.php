<?php

namespace App\Models;

use App\Models\User;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Mood extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['user_id', 'mood', 'date'];

    /**
     * Get the user that owns the mood.
     *
     * This function defines an inverse one-to-many relationship
     * between the Mood model and the User model.
     *
     * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
     */
    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
