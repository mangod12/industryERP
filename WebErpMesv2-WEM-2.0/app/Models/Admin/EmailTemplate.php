<?php

namespace App\Models\Admin;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class EmailTemplate extends Model
{ 
    use HasFactory;

    protected $fillable = ['document_type', 'subject', 'content'];
}
