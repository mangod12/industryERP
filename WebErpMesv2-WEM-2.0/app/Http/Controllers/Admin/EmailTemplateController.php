<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use App\Models\Admin\EmailTemplate;

class EmailTemplateController extends Controller
{
    public function index()
    {
        $emailTemplates = EmailTemplate::all();
        return view('admin/templates-index', compact('emailTemplates'));
    }

    public function store(Request $request)
    {
        $request->validate([
            'document_type' => 'required|string',
            'subject' => 'required|string',
            'content' => 'required|string',
        ]);

        EmailTemplate::create($request->all());

        return redirect()->back()->with('success', 'Modèle de mail créé avec succès !');
    }

    public function update(Request $request, EmailTemplate $emailTemplate)
    {
        $request->validate([
            'subject' => 'required|string',
            'content' => 'required|string',
        ]);

        $emailTemplate->update($request->all());

        return redirect()->back()->with('success', 'Modèle de mail mis à jour !');
    }

    public function destroy(EmailTemplate $emailTemplate)
    {
        $emailTemplate->delete();

        return redirect()->back()->with('success', 'Modèle supprimé avec succès !');
    }
}
