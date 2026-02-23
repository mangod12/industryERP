<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\DocumentCodeTemplate;
use App\Http\Requests\Admin\StoreDocumentCodeTemplateRequest;
use App\Http\Requests\Admin\UpdateDocumentCodeTemplateRequest;

class DocumentCodeTemplateController extends Controller
{
    /**
     * Store a newly created document code template in storage.
     *
     * This method handles the creation of a new document code template.
     * It validates the incoming request using the StoreDocumentCodeTemplateRequest,
     * creates a new DocumentCodeTemplate record in the database with the validated data,
     * and then redirects the user to the 'admin.factory' route with a success message.
     *
     * @param \App\Http\Requests\Admin\StoreDocumentCodeTemplateRequest $request
     * @return \Illuminate\Http\RedirectResponse
     */
    public function store(StoreDocumentCodeTemplateRequest $request)
    {
        DocumentCodeTemplate::create($request->validated());
        return redirect()->route('admin.factory')->with('success', 'Successfully added template code');
    }

    /**
     * Update the specified document code template in storage.
     *
     * This method handles the update of an existing document code template.
     * It validates the incoming request using the UpdateDocumentCodeTemplateRequest,
     * finds the specified DocumentCodeTemplate record by its ID, updates it with the validated data,
     * and then redirects the user to the 'admin.factory' route with a success message.
     *
     * @param \App\Http\Requests\Admin\UpdateDocumentCodeTemplateRequest $request
     * @param int $id The ID of the document code template to update.
     * @return \Illuminate\Http\RedirectResponse
     */
    public function update(UpdateDocumentCodeTemplateRequest $request, $id)
    {
        $documentCodeTemplate = DocumentCodeTemplate::findOrFail($id);
        $documentCodeTemplate->update($request->validated());
        return redirect()->route('admin.factory')->with('success', 'Successfully updated template code');
    }
}
