<?php

namespace App\Http\Controllers\Api;

use Illuminate\Http\Request;
use App\Models\Companies\Companies;
use App\Http\Controllers\Controller;
use App\Http\Resources\CompanieResource;

class CompanyController extends Controller
{
    /**
     * Display the specified resource.
     *
     * @param  \App\Models\Companies\Companies  $id
     */
    public function show(Companies $company)
    {
        return new CompanieResource($company->load(['Contacts', 'Addresses']));
    }

    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return CompanieResource::collection(Companies::with(['Contacts', 'Addresses'])->paginate(10));
    }

    /**
     * Create new company
     */
    public function store(Request $request)
    {
        // validate the request
        $validatedData = $request->validate([
            'code' => 'required|string|unique:companies,code|max:50',
            'label' => 'required|string|max:255',
            'siren' => 'nullable|string|max:14',
            'naf_code' => 'nullable|string|max:10',
            'intra_community_vat' => 'nullable|string|max:20',
            'website' => 'nullable|url|max:255',
            'longitude' => 'nullable|string|max:50',
            'latitude' => 'nullable|string|max:50',
            'user_id' => 'nullable|exists:users,id',
        ]);

        // create new company
        $company = Companies::create($validatedData);

        // return the company
        return new CompanieResource($company);
    }
}
