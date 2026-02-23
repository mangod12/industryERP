<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use App\Http\Resources\AdresseResource;
use App\Http\Resources\ContactResource;
use App\Http\Resources\CompanieResource;
use App\Http\Resources\OrderLinesResource;
use App\Http\Resources\PaymentMethodResource;
use App\Http\Resources\DeleveryMethodResource;
use App\Http\Resources\PaymentConditionResource;
use Illuminate\Http\Resources\Json\JsonResource;

class OrderResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array|\Illuminate\Contracts\Support\Arrayable|\JsonSerializable
     */
    public function toArray($request)
    {

        return [
            'id' => $this->id,
            'uuid' => $this->uuid,          
            'code' => $this->code,
            'label' => $this->label,
            'customer_reference' => $this->customer_reference,
            'companies_id' => new CompanieResource($this->companie),
            'companies_contacts_id' => new ContactResource($this->contact),
            'companies_addresses_id' => new AdresseResource($this->adresse),
            'accounting_payment_conditions_id' => new PaymentConditionResource($this->payment_condition),
            'accounting_payment_methods_id' => new PaymentMethodResource($this->payment_method),
            'accounting_deliveries_id' => new DeleveryMethodResource($this->delevery_method),
            'validity_date' => $this->validity_date,
            'statu' => $this->statu,
            'comment' => $this->comment,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
            'order_lines' => OrderLinesResource::collection($this->OrderLines),
        ];

        //return parent::toArray($request);
    }
}
