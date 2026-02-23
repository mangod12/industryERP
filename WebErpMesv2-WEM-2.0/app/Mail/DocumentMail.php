<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Address;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Queue\SerializesModels;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Mail\Mailables\Attachment;

class DocumentMail extends Mailable
{
    use Queueable, SerializesModels;

    public $document;
    public $data;
    public $attachmentPath;

    /**
     * Create a new message instance.
     */
    public function __construct($document, $data)
    {
        $this->document = $document;
        $this->data = $data;
        $this->attachmentPath = $data['attachment'] ?? null;
    }

    /**
     * Get the message envelope.
     */
    public function envelope(): Envelope
    {
        return new Envelope(
            from: new Address(config('mail.from.address'), config('mail.from.name')),
            subject: $this->data['subject'],
        );
    }

    /**
     * Get the message content definition.
     */
    public function content(): Content
    {
        return new Content(
            view: 'emails.document',
            with: [
                'messageContent' => $this->data['message'],
                'document' => $this->document
            ],
        );
    }

    /**
     * Get the attachments for the message.
     *
     * @return array<int, \Illuminate\Mail\Mailables\Attachment>
     */
    public function attachments(): array
    {
        $attachments = [];

        if ($this->attachmentPath) {
            $attachments[] = Attachment::fromPath(storage_path('app/' . $this->attachmentPath));
        }

        return $attachments;
    }
}
