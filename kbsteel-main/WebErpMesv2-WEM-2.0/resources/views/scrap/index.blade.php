@extends('adminlte::page')

@section('title', 'Scrap Inventory')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-recycle text-warning"></i> Scrap Inventory</h1>
    </div>
    <div class="col-sm-6">
        <div class="float-sm-right">
            <a href="{{ route('scrap.upload.form') }}" class="btn btn-info">
                <i class="fas fa-upload"></i> Upload CSV
            </a>
            <a href="{{ route('scrap.create') }}" class="btn btn-success">
                <i class="fas fa-plus"></i> Add Scrap
            </a>
            <a href="{{ route('scrap.analytics') }}" class="btn btn-purple">
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
        <div class="small-box bg-warning">
            <div class="inner">
                <h3>{{ number_format($stats['total_weight'], 1) }} <sup style="font-size: 20px">kg</sup></h3>
                <p>Total Scrap Weight</p>
            </div>
            <div class="icon"><i class="fas fa-weight-hanging"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-danger">
            <div class="inner">
                <h3>{{ number_format($stats['pending_weight'], 1) }} <sup style="font-size: 20px">kg</sup></h3>
                <p>Pending Review ({{ $stats['pending_count'] }} items)</p>
            </div>
            <div class="icon"><i class="fas fa-clock"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-success">
            <div class="inner">
                <h3>₹{{ number_format($stats['scrap_value'], 0) }}</h3>
                <p>Scrap Value Recovered</p>
            </div>
            <div class="icon"><i class="fas fa-rupee-sign"></i></div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="small-box bg-info">
            <div class="inner">
                <h3>{{ $scrapRecords->total() }}</h3>
                <p>Total Records</p>
            </div>
            <div class="icon"><i class="fas fa-list"></i></div>
        </div>
    </div>
</div>

<!-- Filters -->
<div class="card card-outline card-warning">
    <div class="card-header">
        <h3 class="card-title"><i class="fas fa-filter"></i> Filters</h3>
        <div class="card-tools">
            <button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fas fa-minus"></i></button>
        </div>
    </div>
    <div class="card-body">
        <form method="GET" action="{{ route('scrap.index') }}">
            <div class="row">
                <div class="col-md-3">
                    <select name="material" class="form-control select2">
                        <option value="">-- All Materials --</option>
                        @foreach($materials as $material)
                            <option value="{{ $material }}" {{ request('material') == $material ? 'selected' : '' }}>{{ $material }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="status" class="form-control">
                        <option value="">-- All Status --</option>
                        @foreach($statuses as $key => $label)
                            <option value="{{ $key }}" {{ request('status') == $key ? 'selected' : '' }}>{{ $label }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="col-md-2">
                    <select name="reason" class="form-control">
                        <option value="">-- All Reasons --</option>
                        @foreach($reasonCodes as $key => $label)
                            <option value="{{ $key }}" {{ request('reason') == $key ? 'selected' : '' }}>{{ $label }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="col-md-2">
                    <input type="date" name="date_from" class="form-control" value="{{ request('date_from') }}" placeholder="From Date">
                </div>
                <div class="col-md-2">
                    <input type="date" name="date_to" class="form-control" value="{{ request('date_to') }}" placeholder="To Date">
                </div>
                <div class="col-md-1">
                    <button type="submit" class="btn btn-primary btn-block"><i class="fas fa-search"></i></button>
                </div>
            </div>
        </form>
    </div>
</div>

<!-- Scrap Records Table -->
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Scrap Records</h3>
        <div class="card-tools">
            <form method="POST" action="{{ route('scrap.bulk-action') }}" id="bulkActionForm">
                @csrf
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-default" onclick="selectAll()">Select All Pending</button>
                    <button type="submit" name="action" value="return" class="btn btn-sm btn-success">
                        <i class="fas fa-undo"></i> Return Selected
                    </button>
                    <button type="submit" name="action" value="dispose" class="btn btn-sm btn-danger">
                        <i class="fas fa-trash"></i> Dispose Selected
                    </button>
                </div>
            </form>
        </div>
    </div>
    <div class="card-body table-responsive p-0">
        <table class="table table-hover table-striped">
            <thead>
                <tr>
                    <th><input type="checkbox" id="selectAllCheckbox"></th>
                    <th>ID</th>
                    <th>Material</th>
                    <th>Weight (kg)</th>
                    <th>Dimensions</th>
                    <th>Qty</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Customer</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                @forelse($scrapRecords as $scrap)
                <tr class="{{ $scrap->status == 'pending' ? 'table-warning' : '' }}">
                    <td>
                        @if($scrap->status == 'pending')
                            <input type="checkbox" name="ids[]" form="bulkActionForm" value="{{ $scrap->id }}">
                        @endif
                    </td>
                    <td>{{ $scrap->id }}</td>
                    <td><strong>{{ $scrap->material_name }}</strong></td>
                    <td>{{ number_format($scrap->weight_kg, 2) }}</td>
                    <td>
                        @if($scrap->dimensions)
                            {{ $scrap->dimensions }}
                        @elseif($scrap->length_mm || $scrap->width_mm)
                            {{ $scrap->length_mm }}×{{ $scrap->width_mm }}mm
                        @else
                            -
                        @endif
                    </td>
                    <td>{{ $scrap->quantity }}</td>
                    <td>
                        <span class="badge badge-{{ $scrap->reason_code == 'defect' ? 'danger' : ($scrap->reason_code == 'cutting_waste' ? 'info' : 'secondary') }}">
                            {{ $scrap->reason_label }}
                        </span>
                    </td>
                    <td>
                        @switch($scrap->status)
                            @case('pending')
                                <span class="badge badge-warning">Pending</span>
                                @break
                            @case('returned_to_inventory')
                                <span class="badge badge-success">Returned</span>
                                @break
                            @case('disposed')
                                <span class="badge badge-danger">Disposed</span>
                                @break
                            @case('sold')
                                <span class="badge badge-primary">Sold ₹{{ number_format($scrap->scrap_value) }}</span>
                                @break
                            @default
                                <span class="badge badge-secondary">{{ $scrap->status }}</span>
                        @endswitch
                    </td>
                    <td>{{ $scrap->customer?->name ?? '-' }}</td>
                    <td>{{ $scrap->created_at->format('d M Y') }}</td>
                    <td>
                        <a href="{{ route('scrap.show', $scrap) }}" class="btn btn-xs btn-info">
                            <i class="fas fa-eye"></i>
                        </a>
                        @if($scrap->status == 'pending')
                            <button type="button" class="btn btn-xs btn-success" data-toggle="modal" data-target="#actionModal{{ $scrap->id }}">
                                <i class="fas fa-cog"></i> Action
                            </button>
                        @endif
                    </td>
                </tr>

                <!-- Action Modal -->
                @if($scrap->status == 'pending')
                <div class="modal fade" id="actionModal{{ $scrap->id }}" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <form method="POST" action="{{ route('scrap.action', $scrap) }}">
                                @csrf
                                <div class="modal-header bg-warning">
                                    <h5 class="modal-title">Process Scrap #{{ $scrap->id }}</h5>
                                    <button type="button" class="close" data-dismiss="modal">&times;</button>
                                </div>
                                <div class="modal-body">
                                    <p><strong>Material:</strong> {{ $scrap->material_name }}</p>
                                    <p><strong>Weight:</strong> {{ $scrap->weight_kg }} kg</p>
                                    
                                    <div class="form-group">
                                        <label>Select Action:</label>
                                        <div class="btn-group-vertical w-100">
                                            <label class="btn btn-outline-success">
                                                <input type="radio" name="action" value="return"> 
                                                <i class="fas fa-undo"></i> Return to Main Inventory
                                            </label>
                                            <label class="btn btn-outline-info">
                                                <input type="radio" name="action" value="reusable"> 
                                                <i class="fas fa-boxes"></i> Move to Reusable Stock
                                            </label>
                                            <label class="btn btn-outline-danger">
                                                <input type="radio" name="action" value="dispose"> 
                                                <i class="fas fa-trash"></i> Mark as Disposed
                                            </label>
                                            <label class="btn btn-outline-primary">
                                                <input type="radio" name="action" value="sell"> 
                                                <i class="fas fa-rupee-sign"></i> Mark as Sold
                                            </label>
                                        </div>
                                    </div>

                                    <div class="form-group" id="gradeGroup" style="display:none;">
                                        <label>Quality Grade (for Reusable):</label>
                                        <select name="quality_grade" class="form-control">
                                            <option value="A">Grade A - Excellent</option>
                                            <option value="B">Grade B - Minor defects</option>
                                            <option value="C">Grade C - Usable with caution</option>
                                        </select>
                                    </div>

                                    <div class="form-group" id="valueGroup" style="display:none;">
                                        <label>Sale Value (₹):</label>
                                        <input type="number" name="scrap_value" class="form-control" step="0.01" min="0">
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-primary">Process</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                @endif
                @empty
                <tr>
                    <td colspan="11" class="text-center text-muted">No scrap records found</td>
                </tr>
                @endforelse
            </tbody>
        </table>
    </div>
    <div class="card-footer">
        {{ $scrapRecords->withQueryString()->links() }}
    </div>
</div>
@stop

@section('js')
<script>
    // Show/hide conditional fields based on action selection
    $('input[name="action"]').change(function() {
        var action = $(this).val();
        var modal = $(this).closest('.modal');
        
        modal.find('#gradeGroup').toggle(action === 'reusable');
        modal.find('#valueGroup').toggle(action === 'sell');
    });

    // Select all pending checkboxes
    function selectAll() {
        $('input[name="ids[]"]').prop('checked', true);
    }

    $('#selectAllCheckbox').change(function() {
        $('input[name="ids[]"]').prop('checked', this.checked);
    });
</script>
@stop
