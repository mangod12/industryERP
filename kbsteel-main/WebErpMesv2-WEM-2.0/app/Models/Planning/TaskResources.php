<?php

namespace App\Models\Planning;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class TaskResources extends Model
{
    use HasFactory;

    // Fillable attributes for mass assignment
    protected $fillable= ['task_id', 
                            'methods_ressources_id',
                            'autoselected_ressource',
                            'userforced_ressource',];
}
