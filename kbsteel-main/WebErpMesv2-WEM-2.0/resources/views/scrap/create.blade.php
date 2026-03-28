@extends('adminlte::page')

@section('title', 'Add Scrap Entry')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-plus-circle text-warning"></i> Add Scrap Entry</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('scrap.index') }}">Scrap Inventory</a></li>
            <li class="breadcrumb-item active">Add New</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<div class="card card-warning">
    <div class="card-header">
        <h3 class="card-title">Scrap Details</h3>
    </div>
    <form method="POST" action="{{ route('scrap.store') }}">
        @csrf
        <div class="card-body">
            @if($errors->any())
                <div class="alert alert-danger">
                    <ul class="mb-0">
                        @foreach($errors->all() as $error)
                            <li>{{ $error }}</li>
                        @endforeach
                    </ul>
                </div>
            @endif

            <div class="row">
                <div class="col-md-6">
                    <div class="form-group">
                        <label>Material Name <span class="text-danger">*</span></label>
                        <select name="material_name" class="form-control select2" required>
                            <option value="">-- Select Material --</option>
                            @foreach(config('steel.material_types') as $material)
                                <option value="{{ $material }}" {{ old('material_name') == $material ? 'selected' : '' }}>
                                    {{ $material }}
                                </option>
                            @endforeach
                        </select>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Weight (kg) <span class="text-danger">*</span></label>
                        <input type="number" name="weight_kg" class="form-control" step="0.01" min="0.01" 
                               value="{{ old('weight_kg') }}" required>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Quantity</label>
                        <input type="number" name="quantity" class="form-control" min="1" 
                               value="{{ old('quantity', 1) }}">
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Length (mm)</label>
                        <input type="number" name="length_mm" class="form-control" step="0.1" min="0" 
                               value="{{ old('length_mm') }}">
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Width (mm)</label>
                        <input type="number" name="width_mm" class="form-control" step="0.1" min="0" 
                               value="{{ old('width_mm') }}">
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Thickness (mm)</label>
                        <input type="number" name="thickness_mm" class="form-control" step="0.1" min="0" 
                               value="{{ old('thickness_mm') }}">
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Or Dimensions (free text)</label>
                        <input type="text" name="dimensions" class="form-control" 
                               value="{{ old('dimensions') }}" placeholder="e.g., 500x200x10mm">
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Reason Code <span class="text-danger">*</span></label>
                        <select name="reason_code" class="form-control" required>
                            <option value="">-- Select Reason --</option>
                            @foreach(config('steel.scrap.reason_codes', ['cutting_waste' => 'Cutting Waste', 'defect' => 'Manufacturing Defect', 'damage' => 'Handling Damage', 'overrun' => 'Production Overrun', 'leftover' => 'Leftover Material']) as $code => $label)
                                <option value="{{ $code }}" {{ old('reason_code') == $code ? 'selected' : '' }}>
                                    {{ $label }}
                                </option>
                            @endforeach
                        </select>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Production Stage</label>
                        <select name="stage" class="form-control">
                            <option value="">-- Select Stage --</option>
                            @foreach(config('steel.production_stages', ['fabrication' => ['name' => 'Fabrication'], 'painting' => ['name' => 'Painting'], 'dispatch' => ['name' => 'Ready for Dispatch']]) as $stage => $info)
                                <option value="{{ $stage }}" {{ old('stage') == $stage ? 'selected' : '' }}>
                                    {{ is_array($info) ? $info['name'] : $info }}
                                </option>
                            @endforeach
                        </select>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Location</label>
                        <input type="text" name="location" class="form-control" 
                               value="{{ old('location') }}" placeholder="e.g., Bay A, Rack 3">
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="form-group">
                        <label>Customer/Project (optional)</label>
                        <select name="customer_id" class="form-control select2">
                            <option value="">-- No Customer --</option>
                            @foreach($customers ?? [] as $customer)
                                <option value="{{ $customer->id }}" {{ old('customer_id') == $customer->id ? 'selected' : '' }}>
                                    {{ $customer->name }}
                                </option>
                            @endforeach
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="form-group">
                        <label>Work Order Reference</label>
                        <input type="text" name="work_order_id" class="form-control" 
                               value="{{ old('work_order_id') }}" placeholder="Work order ID if applicable">
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" class="form-control" rows="3" 
                          placeholder="Additional notes about this scrap...">{{ old('notes') }}</textarea>
            </div>
        </div>
        <div class="card-footer">
            <button type="submit" class="btn btn-warning">
                <i class="fas fa-save"></i> Save Scrap Entry
            </button>
            <a href="{{ route('scrap.index') }}" class="btn btn-secondary">
                <i class="fas fa-times"></i> Cancel
            </a>
        </div>
    </form>
</div>
@stop

@section('js')
<script>
    $(document).ready(function() {
        $('.select2').select2();
    });
</script>
@stop
