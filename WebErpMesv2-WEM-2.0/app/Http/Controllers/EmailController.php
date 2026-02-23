<?php

namespace App\Http\Controllers;

use App\Mail\DocumentMail;
use Illuminate\Http\Request;
use App\Models\Admin\EmailTemplate;
use Illuminate\Support\Facades\Mail;

class EmailController extends Controller
{
    protected $models = [
        'order' => \App\Models\Workflow\Orders::class,
        'quote' => \App\Models\Workflow\Quotes::class,
        'delivery' => \App\Models\Workflow\Deliverys::class,
        'invoice' => \App\Models\Workflow\Invoices::class,
        'creditnote' => \App\Models\Workflow\CreditNotes::class,
        'purchase' => \App\Models\Purchases\Purchases::class,
        'purchase-quotation' => \App\Models\Purchases\PurchasesQuotation::class,
    ];

    /**
     * Create a new email view for the specified model type and ID.
     *
     * @param string $type The type of the model.
     * @param int $id The ID of the model.
     * @return \Illuminate\View\View The view for creating an email.
     * @throws \Illuminate\Database\Eloquent\ModelNotFoundException If the model is not found.
     * @throws \Symfony\Component\HttpKernel\Exception\NotFoundHttpException If the model type is not defined.
     */
    public function create($type, $id)
    {
        if (!isset($this->models[$type])) {
            abort(404);
        }

        // Retrieve the document instance
        $model = $this->models[$type]::findOrFail($id);
        $contactMail = $model->contact->mail;
        // Search for the corresponding email template
        $emailTemplate = EmailTemplate::where('document_type', $type, $contactMail)->first();

        // Retrieve the object (document code)
        if($emailTemplate) {
            $object = $emailTemplate->subject .' '. $model->code;
        } else {
            $object = 'N/A';
        }

        //recorde last model url
        session(['previous_url' => url()->previous()]);

       // Pass data to the view
        return view('emails.create', compact('model', 'type', 'object', 'emailTemplate', 'contactMail'));
    }

    /**
     * Send an email with the specified type and ID.
     *
     * @param \Illuminate\Http\Request $request The incoming request instance.
     * @param string $type The type of the model to send the email for.
     * @param int $id The ID of the model instance.
     * @return \Illuminate\Http\RedirectResponse Redirects back with a success message.
     */
    public function send(Request $request, $type, $id)
    {
        // Check if the provided type exists in the models array
        if (!isset($this->models[$type])) {
            abort(404); // Abort with a 404 error if the type is not found
        }
    
        // Retrieve the model instance by ID
        $model = $this->models[$type]::findOrFail($id);
    
        // Validate the incoming request data
        $request->validate([
            'to' => 'required|email',
            'subject' => 'required|string',
            'message' => 'required|string',
            'attachment' => 'nullable|file|max:2048',
        ]);
    
        // Prepare the email data
        $data = [
            'to' => $request->to,
            'subject' => $request->subject,
            'message' => $request->message,
        ];
    
        // Check if an attachment is provided and store it
        if ($request->hasFile('attachment')) {
            $path = $request->file('attachment')->store('attachments');
            $data['attachment'] = $path;
        }
    
        // Send the email using the DocumentMail Mailable class
        Mail::to($data['to'])->send(new DocumentMail($model, $data));
    
        // Log the email details in the email logs
        $model->emailLogs()->create([
            'to' => $data['to'],
            'subject' => $data['subject'],
            'message' => $data['message'],
            'attachment' => $data['attachment'] ?? null,
        ]);
    
        // Redirect back with a success message
        return redirect(session('previous_url', url('/')))->with('success', 'E-mail envoyé avec succès !');

    }
}
