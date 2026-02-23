@extends('adminlte::page')

@section('title', 'Find Matching Stock')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-search text-primary"></i> Find Matching Reusable Stock</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('reusable.index') }}">Reusable Stock</a></li>
            <li class="breadcrumb-item active">Find Match</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<div class="row">
    <!-- Search Form -->
    <div class="col-md-4">
        <div class="card card-primary">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-ruler-combined"></i> Required Dimensions</h3>
            </div>
            <form method="GET" action="{{ route('reusable.find-match') }}">
                <div class="card-body">
                    <div class="form-group">
                        <label>Material Type <span class="text-danger">*</span></label>
                        <select name="material" class="form-control select2" required>
                            <option value="">-- Select Material --</option>
                            @foreach(config('steel.material_types') as $material)
                                <option value="{{ $material }}" {{ request('material') == $material ? 'selected' : '' }}>
                                    {{ $material }}
                                </option>
                            @endforeach
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Minimum Length (mm) <span class="text-danger">*</span></label>
                        <input type="number" name="min_length" class="form-control" step="1" min="1" 
                               value="{{ request('min_length') }}" required>
                    </div>

                    <div class="form-group">
                        <label>Minimum Width (mm) <span class="text-danger">*</span></label>
                        <input type="number" name="min_width" class="form-control" step="1" min="1" 
                               value="{{ request('min_width') }}" required>
                    </div>

                    <div class="form-group">
                        <label>Thickness (mm)</label>
                        <input type="number" name="thickness" class="form-control" step="0.1" 
                               value="{{ request('thickness') }}">
                        <small class="text-muted">Leave empty for any thickness</small>
                    </div>

                    <div class="form-group">
                        <label>Minimum Grade</label>
                        <select name="min_grade" class="form-control">
                            <option value="">-- Any Grade --</option>
                            <option value="A" {{ request('min_grade') == 'A' ? 'selected' : '' }}>Grade A only</option>
                            <option value="B" {{ request('min_grade') == 'B' ? 'selected' : '' }}>Grade B or better</option>
                            <option value="C" {{ request('min_grade') == 'C' ? 'selected' : '' }}>Any grade</option>
                        </select>
                    </div>
                </div>
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary btn-block">
                        <i class="fas fa-search"></i> Find Matches
                    </button>
                </div>
            </form>
        </div>

        <!-- Tips Card -->
        <div class="card card-outline card-secondary">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-lightbulb"></i> Search Tips</h3>
            </div>
            <div class="card-body">
                <ul class="mb-0">
                    <li>Enter the <strong>minimum</strong> dimensions you need</li>
                    <li>Results show stock that's equal or larger</li>
                    <li>Sorted by closest match first</li>
                    <li>Grade A items shown first when tied</li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Results -->
    <div class="col-md-8">
        @if(isset($matches))
            @if($matches->count() > 0)
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> 
                    Found <strong>{{ $matches->count() }}</strong> matching items for 
                    <strong>{{ request('material') }}</strong> ≥ {{ request('min_length') }} × {{ request('min_width') }} mm
                </div>

                @foreach($matches as $item)
                <div class="card card-outline card-{{ $item->quality_grade == 'A' ? 'success' : ($item->quality_grade == 'B' ? 'warning' : 'danger') }}">
                    <div class="card-header">
                        <h3 class="card-title">
                            <span class="badge badge-{{ $item->quality_grade == 'A' ? 'success' : ($item->quality_grade == 'B' ? 'warning' : 'danger') }}">
                                Grade {{ $item->quality_grade }}
                            </span>
                            {{ $item->material_name }}
                            <small class="text-muted ml-2">#{{ $item->id }}</small>
                        </h3>
                        <div class="card-tools">
                            <span class="badge badge-primary">
                                {{ number_format($item->length_mm) }} × {{ number_format($item->width_mm) }} mm
                            </span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <table class="table table-sm table-borderless mb-0">
                                    <tr>
                                        <th>Dimensions:</th>
                                        <td>
                                            {{ $item->length_mm }} × {{ $item->width_mm }}
                                            @if($item->thickness_mm) × {{ $item->thickness_mm }} @endif mm
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>Weight:</th>
                                        <td>{{ number_format($item->weight_kg, 2) }} kg</td>
                                    </tr>
                                    <tr>
                                        <th>Location:</th>
                                        <td>{{ $item->location ?? 'Not specified' }}</td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <table class="table table-sm table-borderless mb-0">
                                    <tr>
                                        <th>Excess Length:</th>
                                        <td class="text-success">+{{ $item->length_mm - request('min_length') }} mm</td>
                                    </tr>
                                    <tr>
                                        <th>Excess Width:</th>
                                        <td class="text-success">+{{ $item->width_mm - request('min_width') }} mm</td>
                                    </tr>
                                    <tr>
                                        <th>In Stock Since:</th>
                                        <td>{{ $item->created_at->diffForHumans() }}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                        @if($item->notes)
                            <hr class="my-2">
                            <small class="text-muted"><i class="fas fa-sticky-note"></i> {{ $item->notes }}</small>
                        @endif
                    </div>
                    <div class="card-footer">
                        <form method="POST" action="{{ route('reusable.mark-used', $item) }}" class="d-inline">
                            @csrf
                            <button type="submit" class="btn btn-success" onclick="return confirm('Use this stock for production?')">
                                <i class="fas fa-check"></i> Use This Stock
                            </button>
                        </form>
                        <a href="{{ route('reusable.show', $item) }}" class="btn btn-info">
                            <i class="fas fa-eye"></i> View Details
                        </a>
                    </div>
                </div>
                @endforeach
            @else
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> 
                    No matching stock found for <strong>{{ request('material') }}</strong> 
                    ≥ {{ request('min_length') }} × {{ request('min_width') }} mm
                </div>

                <div class="card">
                    <div class="card-body text-center py-5">
                        <i class="fas fa-inbox fa-4x text-muted mb-3"></i>
                        <h4>No Matches Found</h4>
                        <p class="text-muted">Try adjusting your search criteria or check available stock.</p>
                        <a href="{{ route('reusable.index') }}" class="btn btn-primary">
                            <i class="fas fa-list"></i> Browse All Stock
                        </a>
                    </div>
                </div>
            @endif
        @else
            <div class="card">
                <div class="card-body text-center py-5">
                    <i class="fas fa-search fa-4x text-primary mb-3"></i>
                    <h4>Enter Dimensions to Search</h4>
                    <p class="text-muted">
                        Specify the minimum dimensions you need and we'll find matching reusable stock pieces.
                    </p>
                </div>
            </div>

            <!-- Quick Stats -->
            <div class="row mt-3">
                <div class="col-md-4">
                    <div class="info-box bg-gradient-info">
                        <span class="info-box-icon"><i class="fas fa-boxes"></i></span>
                        <div class="info-box-content">
                            <span class="info-box-text">Available Items</span>
                            <span class="info-box-number">{{ $availableCount ?? 0 }}</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="info-box bg-gradient-success">
                        <span class="info-box-icon"><i class="fas fa-star"></i></span>
                        <div class="info-box-content">
                            <span class="info-box-text">Grade A Items</span>
                            <span class="info-box-number">{{ $gradeACount ?? 0 }}</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="info-box bg-gradient-primary">
                        <span class="info-box-icon"><i class="fas fa-weight-hanging"></i></span>
                        <div class="info-box-content">
                            <span class="info-box-text">Total Weight</span>
                            <span class="info-box-number">{{ number_format($totalWeight ?? 0, 1) }} kg</span>
                        </div>
                    </div>
                </div>
            </div>
        @endif
    </div>
</div>
@stop

@section('js')
<script>
    $(document).ready(function() {
        $('.select2').select2();
    });
</script>
@stop
