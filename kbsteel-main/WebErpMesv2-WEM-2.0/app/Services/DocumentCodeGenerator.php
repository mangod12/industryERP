<?php

namespace App\Services;

use App\Models\DocumentCodeTemplate;
use Carbon\Carbon;

class DocumentCodeGenerator
{
    //Default template if none found for given document type
    protected $defaultTemplate = '{type}-{id}';

    /**
     * Generate a document code based on a template and the document type.
     *
     * This method generates a unique document code using a predefined template for the given document type.
     * It retrieves the template from the DocumentCodeTemplate model, replaces placeholders in the template
     * with dynamic values such as the current year, month, day, and an incremented ID, and returns the generated code.
     *
     * @param string $documentType The type of the document for which to generate the code.
     * @param int|null $lastId The last used ID for the document type, used to increment the new ID. Defaults to null.
     * @return string The generated document code.
     */
    public function generateDocumentCode(string $documentType, int $lastId = null)
    {
        // Retrieve the code template for the given document type
        $template = DocumentCodeTemplate::getTemplateForDocument($documentType);

        // If no last ID, start at 0
        $id = $lastId ? $lastId + 1 : 0;

        // Replace placeholders with dynamic values
        $code = str_replace('{year}', Carbon::now()->format('Y'), $template);
        $code = str_replace('{month}', Carbon::now()->format('m'), $code);
        $code = str_replace('{day}', Carbon::now()->format('d'), $code);
        $code = str_replace('{id}', $id, $code);
        $code = str_replace('{type}', strtoupper($documentType), $code);

        return $code;
    }
}
