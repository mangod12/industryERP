@extends('adminlte::page')

@section('title', 'Add Reusable Stock')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-plus-circle text-info"></i> Add Reusable Stock</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('reusable.index') }}">Reusable Stock</a></li>
            <li class="breadcrumb-item active">Add New</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<div class="card card-info">
    <div class="card-header">
        <h3 class="card-title">Stock Details</h3>
    </div>
    <form method="POST" action="{{ route('reusable.store') }}">
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
                        <label>Material Type <span class="text-danger">*</span></label>
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
                        <label>Length (mm) <span class="text-danger">*</span></label>
                        <input type="number" name="length_mm" class="form-control" step="0.1" min="1" 
                               value="{{ old('length_mm') }}" required>
                        <small class="text-muted">Required for find-match</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-group">
                        <label>Width (mm) <span class="text-danger">*</span></label>
                        <input type="number" name="width_mm" class="form-control" step="0.1" min="1" 
                               value="{{ old('width_mm') }}" required>
                        <small class="text-muted">Required for find-match</small>
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
                        <label>Quality Grade <span class="text-danger">*</span></label>
                        <select name="quality_grade" class="form-control" required>
                            <option value="A" {{ old('quality_grade') == 'A' ? 'selected' : '' }}>
                                Grade A - Excellent condition
                            </option>
                            <option value="B" {{ old('quality_grade', 'B') == 'B' ? 'selected' : '' }}>
                                Grade B - Minor defects
                            </option>
                            <option value="C" {{ old('quality_grade') == 'C' ? 'selected' : '' }}>
                                Grade C - Usable with caution
                            </option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Location</label>
                        <input type="text" name="location" class="form-control" 
                               value="{{ old('location') }}" placeholder="e.g., Bay A, Rack 3, Shelf 2">
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Source Scrap ID</label>
                        <input type="text" name="scrap_record_id" class="form-control" 
                               value="{{ old('scrap_record_id') }}" placeholder="Original scrap record ID">
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status" class="form-control">
                            <option value="available">Available</option>
                            <option value="reserved">Reserved</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" class="form-control" rows="3" 
                          placeholder="Any additional notes about condition, origin, etc.">{{ old('notes') }}</textarea>
            </div>

            <!-- Grade Guidelines -->
            <div class="callout callout-info">
                <h5><i class="fas fa-info-circle"></i> Quality Grade Guidelines</h5>
                <div class="row">
                    <div class="col-md-4">
                        <strong class="text-success">Grade A:</strong>
                        <ul class="mb-0">
                            <li>No visible defects</li>
                            <li>Clean, straight edges</li>
                            <li>Suitable for primary use</li>
                        </ul>
                    </div>
                    <div class="col-md-4">
                        <strong class="text-warning">Grade B:</strong>
                        <ul class="mb-0">
                            <li>Minor surface marks</li>
                            <li>Slight edge irregularities</li>
                            <li>Good for secondary work</li>
                        </ul>
                    </div>
                    <div class="col-md-4">
                        <strong class="text-danger">Grade C:</strong>
                        <ul class="mb-0">
                            <li>Visible defects/rust</li>
                            <li>Irregular edges</li>
                            <li>Use with extra care</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        <div class="card-footer">
            <button type="submit" class="btn btn-info">
                <i class="fas fa-save"></i> Save to Reusable Stock
            </button>
            <a href="{{ route('reusable.index') }}" class="btn btn-secondary">
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
