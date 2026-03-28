<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Workflow\Orders;

use App\Http\Resources\OrderResource;

class OrderController extends Controller
{
    /**
     * Display the specified resource.
     *
     * @param  \App\Models\Workflow\Orders  $order
     * @return \App\Http\Resources\OrderResource
     */
    public function show(Orders $order)
    {
        return new OrderResource($order);
    }

    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return OrderResource::collection(Orders::with(['companie', 'contact', 'adresse', 'OrderLines'])->paginate(10));
    }
}
