<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class DocumentCodeTemplate extends Model
{
    // Allow mass assignment for these columns
    protected $fillable = ['document_type', 'template'];
    
    /**
     *Allows to retrieve a default template if none is found
     */
    public static function getTemplateForDocument(string $documentType): string
    {
        // Search the database for a template matching the document type
        $template = self::where('document_type', $documentType)->first();

        // If no template is found, we return a default template
        return $template ? $template->template : '{type}-{id}';
    }
}
