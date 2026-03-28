<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class EmailLog extends Model
{
    use HasFactory;

    protected $fillable = ['to', 'subject', 'message', 'attachment'];

    public function emailable()
    {
        return $this->morphTo();
    }

    public function emailLogs()
    {
        return $this->morphMany(EmailLog::class, 'emailable');
    }
}
