<?php

namespace App\Listeners;

use App\Mail\WelcomeMail;
use Illuminate\Auth\Events\Registered;
use Illuminate\Support\Facades\Mail;

class SendWelcomeEmail
{
    /**
     * Create the event listener.
     */
    public function __construct()
    {
        //
    }

   /**
     * Handle the event.
     */
    public function handle(Registered $event): void
    {
        $user = $event->user;

        // Envoyer l'email avec un mot de passe temporaire
        $password = 'MotDePasseTemporaire123'; // Ici, si besoin

        Mail::to($user->email)->send(new WelcomeMail($user));
    }
}
