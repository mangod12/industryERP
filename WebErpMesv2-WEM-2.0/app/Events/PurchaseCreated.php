<?php

namespace App\Events;

use Illuminate\Queue\SerializesModels;
use Illuminate\Broadcasting\PrivateChannel;
use App\Models\Purchases\PurchasesQuotation;
use Illuminate\Foundation\Events\Dispatchable;

class PurchaseCreated
{
    use Dispatchable, SerializesModels;

    public $purchasesQuotation;

    /**
     * Create a new event instance.
     *
     * @return void
     */
    public function __construct(PurchasesQuotation $purchasesQuotation)
    {
        $this->purchasesQuotation = $purchasesQuotation;
    }

        /**
     * Get the channels the event should broadcast on.
     *
     * @return array<int, \Illuminate\Broadcasting\Channel>
     */
    public function broadcastOn(): array
    {
        return [
            new PrivateChannel('channel-name'),
        ];
    }
}