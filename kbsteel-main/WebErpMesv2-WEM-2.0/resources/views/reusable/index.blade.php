@extends('adminlte::page')

@section('title', 'Reusable Stock')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-boxes text-info"></i> Reusable Stock Inventory</h1>
    </div>
    <div class="col-sm-6">
        <div class="float-sm-right">
            <a href="{{ route('reusable.find-match') }}" class="btn btn-primary">
                <i class="fas fa-search"></i> Find Match
            </a>
            <a href="{{ route('reusable.create') }}" class="btn btn-success">
                <i class="fas fa-plus"></i> Add Stock
            </a>
            <a href="{{ route('reusable.analytics') }}" class="btn btn-purple">
                <i class="fas fa-chart-pie"></i> Analytics
            </a>
        </div>
    </div>
</div>
@stop

@section('content')
<!-- Statistics Cards -->
<div class="row">
    <div class="col-lg-3 col-6">
        <div class="small-box bg-info">
            <div class="inner">
                <h3>{{ number_format($stats['available_weight'], 1) }} <sup style="font-size: 20px">kg</sup></h3>
                <p>Available Stock</p>
            </div>
            <div class="icon"><i class="fas fa-cubes"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-success">
            <div class="inner">
                <h3>{{ $stats['available_count'] }}</h3>
                <p>Available Items</p>
            </div>
            <div class="icon"><i class="fas fa-check-circle"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-warning">
            <div class="inner">
                <h3>{{ number_format($stats['used_weight'], 1) }} <sup style="font-size: 20px">kg</sup></h3>
                <p>Used This Month</p>
            </div>
            <div class="icon"><i class="fas fa-industry"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-primary">
            <div class="inner">
                <h3>₹{{ number_format($stats['estimated_value'], 0) }}</h3>
                <p>Estimated Value</p>
            </div>
            <div class="icon"><i class="fas fa-rupee-sign"></i></div>
        </div>
    </div>
</div>

<!-- Filters -->
<div class="card card-outline card-info">
    <div class="card-header">
        <h3 class="card-title"><i class="fas fa-filter"></i> Filters</h3>
        <div class="card-tools">
            <button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fas fa-minus"></i></button>
        </div>
    </div>
    <div class="card-body">
        <form method="GET" action="{{ route('reusable.index') }}">
            <div class="row">
                <div class="col-md-2">
                    <select name="material" class="form-control select2">
                        <option value="">-- Material --</option>
                        @foreach($materials as $material)
                            <option value="{{ $material }}" {{ request('material') == $material ? 'selected' : '' }}>{{ $material }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="grade" class="form-control">
                        <option value="">-- Grade --</option>
                        <option value="A" {{ request('grade') == 'A' ? 'selected' : '' }}>Grade A</option>
                        <option value="B" {{ request('grade') == 'B' ? 'selected' : '' }}>Grade B</option>
                        <option value="C" {{ request('grade') == 'C' ? 'selected' : '' }}>Grade C</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="status" class="form-control">
                        <option value="">-- Status --</option>
                        <option value="available" {{ request('status') == 'available' ? 'selected' : '' }}>Available</option>
                        <option value="reserved" {{ request('status') == 'reserved' ? 'selected' : '' }}>Reserved</option>
                        <option value="used" {{ request('status') == 'used' ? 'selected' : '' }}>Used</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <input type="number" name="min_length" class="form-control" placeholder="Min Length (mm)" 
                           value="{{ request('min_length') }}">
                </div>
                <div class="col-md-2">
                    <input type="number" name="min_width" class="form-control" placeholder="Min Width (mm)" 
                           value="{{ request('min_width') }}">
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-info btn-block"><i class="fas fa-search"></i> Search</button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Reusable Stock Table -->
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Reusable Stock Items</h3>
        <div class="card-tools">
            <form method="POST" action="{{ route('reusable.bulk-action') }}" id="bulkForm">
                @csrf
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-default" onclick="selectAllAvailable()">Select Available</button>
                    <button type="submit" name="action" value="return" class="btn btn-sm btn-success">
                        <i class="fas fa-undo"></i> Return to Inventory
                    </button>
                    <button type="submit" name="action" value="scrap" class="btn btn-sm btn-warning">
                        <i class="fas fa-recycle"></i> Move to Scrap
                    </button>
                </div>
            </form>
        </div>
    </div>
    <div class="card-body table-responsive p-0">
        <table class="table table-hover table-striped">
            <thead>
                <tr>
                    <th><input type="checkbox" id="selectAll"></th>
                    <th>ID</th>
                    <th>Material</th>
                    <th>Dimensions</th>
                    <th>Weight</th>
                    <th>Grade</th>
                    <th>Status</th>
                    <th>Location</th>
                    <th>Age</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                @forelse($reusableStock as $item)
                <tr class="{{ $item->status == 'reserved' ? 'table-warning' : '' }}">
                    <td>
                        @if($item->status == 'available')
                            <input type="checkbox" name="ids[]" form="bulkForm" value="{{ $item->id }}">
                        @endif
                    </td>
                    <td>{{ $item->id }}</td>
                    <td><strong>{{ $item->material_name }}</strong></td>
                    <td>
                        @if($item->length_mm && $item->width_mm)
                            <span class="badge badge-light">
                                {{ $item->length_mm }} × {{ $item->width_mm }}
                                @if($item->thickness_mm)× {{ $item->thickness_mm }}@endif mm
                            </span>
                        @elseif($item->dimensions)
                            {{ $item->dimensions }}
                        @else
                            -
                        @endif
                    </td>
                    <td>{{ number_format($item->weight_kg, 2) }} kg</td>
                    <td>
                        @switch($item->quality_grade)
                            @case('A')
                                <span class="badge badge-success">Grade A</span>
                                @break
                            @case('B')
                                <span class="badge badge-warning">Grade B</span>
                                @break
                            @case('C')
                                <span class="badge badge-danger">Grade C</span>
                                @break
                        @endswitch
                    </td>
                    <td>
                        @switch($item->status)
                            @case('available')
                                <span class="badge badge-success">Available</span>
                                @break
                            @case('reserved')
                                <span class="badge badge-warning">Reserved</span>
                                @break
                            @case('used')
                                <span class="badge badge-secondary">Used</span>
                                @break
                        @endswitch
                    </td>
                    <td>{{ $item->location ?? '-' }}</td>
                    <td>
                        <small class="text-muted">{{ $item->created_at->diffForHumans() }}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <a href="{{ route('reusable.show', $item) }}" class="btn btn-info" title="View">
                                <i class="fas fa-eye"></i>
                            </a>
                            @if($item->status == 'available')
                                <form method="POST" action="{{ route('reusable.mark-used', $item) }}" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-success" title="Mark Used" 
                                            onclick="return confirm('Mark this item as used?')">
                                        <i class="fas fa-check"></i>
                                    </button>
                                </form>
                                <form method="POST" action="{{ route('reusable.mark-scrap', $item) }}" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-warning" title="Send to Scrap"
                                            onclick="return confirm('Send back to scrap?')">
                                        <i class="fas fa-recycle"></i>
                                    </button>
                                </form>
                            @elseif($item->status == 'reserved')
                                <form method="POST" action="{{ route('reusable.return-available', $item) }}" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-primary" title="Release Reservation">
                                        <i class="fas fa-unlock"></i>
                                    </button>
                                </form>
                            @endif
                        </div>
                    </td>
                </tr>
                @empty
                <tr>
                    <td colspan="10" class="text-center text-muted py-4">
                        <i class="fas fa-inbox fa-3x mb-3 d-block"></i>
                        No reusable stock found
                    </td>
                </tr>
                @endforelse
            </tbody>
        </table>
    </div>
    <div class="card-footer">
        {{ $reusableStock->withQueryString()->links() }}
    </div>
</div>

<!-- Quick Find Modal -->
<div class="modal fade" id="quickFindModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-primary">
                <h5 class="modal-title"><i class="fas fa-search"></i> Quick Find Match</h5>
                <button type="button" class="close" data-dismiss="modal">&times;</button>
            </div>
            <form method="GET" action="{{ route('reusable.find-match') }}">
                <div class="modal-body">
                    <div class="form-group">
                        <label>Material Type</label>
                        <select name="material" class="form-control" required>
                            @foreach(config('steel.material_types') as $material)
                                <option value="{{ $material }}">{{ $material }}</option>
                            @endforeach
                        </select>
                    </div>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="form-group">
                                <label>Min Length (mm)</label>
                                <input type="number" name="min_length" class="form-control" required>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label>Min Width (mm)</label>
                                <input type="number" name="min_width" class="form-control" required>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label>Thickness (mm)</label>
                                <input type="number" name="thickness" class="form-control">
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-primary"><i class="fas fa-search"></i> Find</button>
                </div>
            </form>
        </div>
    </div>
</div>
@stop

@section('js')
<script>
    function selectAllAvailable() {
        $('input[name="ids[]"]').prop('checked', true);
    }

    $('#selectAll').change(function() {
        $('input[name="ids[]"]').prop('checked', this.checked);
    });
</script>
@stop
