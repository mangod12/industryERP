<?php

namespace App\Models\Planning;

use App\Models\Planning\Task;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Status extends Model
{
    // Fillable attributes for mass assignment
    protected $fillable= ['title', 'order'];

    public $timestamps = false;

    public function tasks()
    {
        return $this->hasMany(Task::class)->orderBy('ordre')->whereNotNull('order_lines_id');
    }
}
