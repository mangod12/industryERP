@extends('adminlte::page')

@section('title', 'Scrap Details')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-recycle text-warning"></i> Scrap Record #{{ $scrap->id }}</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('scrap.index') }}">Scrap Inventory</a></li>
            <li class="breadcrumb-item active">Details</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header 
                @switch($scrap->status)
                    @case('pending') bg-warning @break
                    @case('returned_to_inventory') bg-success @break
                    @case('moved_to_reusable') bg-info @break
                    @case('disposed') bg-danger @break
                    @case('sold') bg-primary @break
                    @default bg-secondary
                @endswitch
            ">
                <h3 class="card-title">
                    {{ $scrap->material_name }}
                    <span class="badge badge-light ml-2">{{ strtoupper($scrap->status) }}</span>
                </h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Material Information</h5>
                        <table class="table table-sm table-borderless">
                            <tr>
                                <th width="40%">Material:</th>
                                <td><strong>{{ $scrap->material_name }}</strong></td>
                            </tr>
                            <tr>
                                <th>Weight:</th>
                                <td>{{ number_format($scrap->weight_kg, 2) }} kg</td>
                            </tr>
                            <tr>
                                <th>Quantity:</th>
                                <td>{{ $scrap->quantity }} pcs</td>
                            </tr>
                            <tr>
                                <th>Dimensions:</th>
                                <td>
                                    @if($scrap->dimensions)
                                        {{ $scrap->dimensions }}
                                    @elseif($scrap->length_mm || $scrap->width_mm)
                                        {{ $scrap->length_mm ?? '-' }} × {{ $scrap->width_mm ?? '-' }} × {{ $scrap->thickness_mm ?? '-' }} mm
                                    @else
                                        Not specified
                                    @endif
                                </td>
                            </tr>
                            <tr>
                                <th>Location:</th>
                                <td>{{ $scrap->location ?? 'Not specified' }}</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h5>Scrap Information</h5>
                        <table class="table table-sm table-borderless">
                            <tr>
                                <th width="40%">Reason:</th>
                                <td>
                                    <span class="badge badge-{{ $scrap->reason_code == 'defect' ? 'danger' : 'info' }}">
                                        {{ $scrap->reason_label }}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <th>Stage:</th>
                                <td>{{ ucfirst($scrap->stage ?? 'Not specified') }}</td>
                            </tr>
                            <tr>
                                <th>Status:</th>
                                <td>
                                    @switch($scrap->status)
                                        @case('pending')
                                            <span class="badge badge-warning badge-lg">⏳ Pending Review</span>
                                            @break
                                        @case('returned_to_inventory')
                                            <span class="badge badge-success badge-lg">✓ Returned to Inventory</span>
                                            @break
                                        @case('moved_to_reusable')
                                            <span class="badge badge-info badge-lg">📦 Moved to Reusable</span>
                                            @break
                                        @case('disposed')
                                            <span class="badge badge-danger badge-lg">🗑️ Disposed</span>
                                            @break
                                        @case('sold')
                                            <span class="badge badge-primary badge-lg">💰 Sold</span>
                                            @break
                                    @endswitch
                                </td>
                            </tr>
                            @if($scrap->scrap_value)
                            <tr>
                                <th>Sale Value:</th>
                                <td><strong class="text-success">₹{{ number_format($scrap->scrap_value, 2) }}</strong></td>
                            </tr>
                            @endif
                            <tr>
                                <th>Created:</th>
                                <td>{{ $scrap->created_at->format('d M Y, h:i A') }}</td>
                            </tr>
                            @if($scrap->processed_at)
                            <tr>
                                <th>Processed:</th>
                                <td>{{ $scrap->processed_at->format('d M Y, h:i A') }}</td>
                            </tr>
                            @endif
                        </table>
                    </div>
                </div>

                @if($scrap->notes)
                <hr>
                <h5>Notes</h5>
                <p class="bg-light p-3 rounded">{{ $scrap->notes }}</p>
                @endif

                @if($scrap->customer)
                <hr>
                <h5>Customer/Project Reference</h5>
                <p>
                    <i class="fas fa-building"></i> 
                    <strong>{{ $scrap->customer->name }}</strong>
                    @if($scrap->work_order_id)
                        <br><i class="fas fa-file-alt"></i> Work Order: {{ $scrap->work_order_id }}
                    @endif
                </p>
                @endif
            </div>
        </div>

        <!-- Audit Trail -->
        <div class="card card-outline card-secondary">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-history"></i> History</h3>
            </div>
            <div class="card-body">
                <ul class="timeline timeline-inverse">
                    <li class="time-label">
                        <span class="bg-warning">{{ $scrap->created_at->format('d M Y') }}</span>
                    </li>
                    <li>
                        <i class="fas fa-plus bg-success"></i>
                        <div class="timeline-item">
                            <span class="time"><i class="far fa-clock"></i> {{ $scrap->created_at->format('h:i A') }}</span>
                            <h3 class="timeline-header">Scrap Entry Created</h3>
                            <div class="timeline-body">
                                {{ $scrap->weight_kg }} kg of {{ $scrap->material_name }} marked as scrap
                                @if($scrap->createdBy)
                                    by {{ $scrap->createdBy->name }}
                                @endif
                            </div>
                        </div>
                    </li>

                    @if($scrap->processed_at)
                    <li class="time-label">
                        <span class="bg-info">{{ $scrap->processed_at->format('d M Y') }}</span>
                    </li>
                    <li>
                        <i class="fas fa-check bg-primary"></i>
                        <div class="timeline-item">
                            <span class="time"><i class="far fa-clock"></i> {{ $scrap->processed_at->format('h:i A') }}</span>
                            <h3 class="timeline-header">Status Changed to {{ ucfirst(str_replace('_', ' ', $scrap->status)) }}</h3>
                            <div class="timeline-body">
                                @if($scrap->processedBy)
                                    Processed by {{ $scrap->processedBy->name }}
                                @endif
                            </div>
                        </div>
                    </li>
                    @endif

                    <li>
                        <i class="far fa-clock bg-gray"></i>
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Action Panel -->
    <div class="col-md-4">
        @if($scrap->status == 'pending')
        <div class="card card-warning">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-cogs"></i> Process Scrap</h3>
            </div>
            <form method="POST" action="{{ route('scrap.action', $scrap) }}">
                @csrf
                <div class="card-body">
                    <p class="text-muted">Select an action to process this scrap entry:</p>

                    <div class="form-group">
                        <div class="custom-control custom-radio">
                            <input type="radio" id="actionReturn" name="action" value="return" class="custom-control-input">
                            <label class="custom-control-label" for="actionReturn">
                                <i class="fas fa-undo text-success"></i> Return to Main Inventory
                                <br><small class="text-muted">Add back to usable inventory</small>
                            </label>
                        </div>
                    </div>

                    <div class="form-group">
                        <div class="custom-control custom-radio">
                            <input type="radio" id="actionReusable" name="action" value="reusable" class="custom-control-input">
                            <label class="custom-control-label" for="actionReusable">
                                <i class="fas fa-boxes text-info"></i> Move to Reusable Stock
                                <br><small class="text-muted">Keep for potential reuse</small>
                            </label>
                        </div>
                    </div>

                    <div class="form-group" id="gradeField" style="display:none;">
                        <label>Quality Grade:</label>
                        <select name="quality_grade" class="form-control form-control-sm">
                            <option value="A">A - Excellent condition</option>
                            <option value="B">B - Minor defects</option>
                            <option value="C">C - Usable with caution</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <div class="custom-control custom-radio">
                            <input type="radio" id="actionDispose" name="action" value="dispose" class="custom-control-input">
                            <label class="custom-control-label" for="actionDispose">
                                <i class="fas fa-trash text-danger"></i> Dispose
                                <br><small class="text-muted">Mark as disposed/written off</small>
                            </label>
                        </div>
                    </div>

                    <div class="form-group">
                        <div class="custom-control custom-radio">
                            <input type="radio" id="actionSell" name="action" value="sell" class="custom-control-input">
                            <label class="custom-control-label" for="actionSell">
                                <i class="fas fa-rupee-sign text-primary"></i> Sell as Scrap
                                <br><small class="text-muted">Record sale to scrap dealer</small>
                            </label>
                        </div>
                    </div>

                    <div class="form-group" id="valueField" style="display:none;">
                        <label>Sale Value (₹):</label>
                        <input type="number" name="scrap_value" class="form-control" step="0.01" min="0" placeholder="Enter sale amount">
                    </div>
                </div>
                <div class="card-footer">
                    <button type="submit" class="btn btn-warning btn-block">
                        <i class="fas fa-check"></i> Process Scrap
                    </button>
                </div>
            </form>
        </div>
        @else
        <div class="card">
            <div class="card-body text-center">
                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                <h5>Already Processed</h5>
                <p class="text-muted">This scrap has been processed as:<br>
                    <strong>{{ ucfirst(str_replace('_', ' ', $scrap->status)) }}</strong>
                </p>
            </div>
        </div>
        @endif

        <!-- Quick Stats -->
        <div class="card card-outline card-info">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-calculator"></i> Quick Stats</h3>
            </div>
            <div class="card-body p-0">
                <table class="table table-sm">
                    <tr>
                        <td>Total Weight</td>
                        <td class="text-right"><strong>{{ number_format($scrap->weight_kg * $scrap->quantity, 2) }} kg</strong></td>
                    </tr>
                    <tr>
                        <td>Est. Value/kg</td>
                        <td class="text-right">~₹{{ config('steel.analytics.scrap_value_per_kg', 25) }}</td>
                    </tr>
                    <tr class="bg-light">
                        <td><strong>Est. Total Value</strong></td>
                        <td class="text-right"><strong class="text-success">₹{{ number_format($scrap->weight_kg * $scrap->quantity * config('steel.analytics.scrap_value_per_kg', 25), 0) }}</strong></td>
                    </tr>
                </table>
            </div>
        </div>

        <a href="{{ route('scrap.index') }}" class="btn btn-secondary btn-block">
            <i class="fas fa-arrow-left"></i> Back to List
        </a>
    </div>
</div>
@stop

@section('js')
<script>
    $('input[name="action"]').change(function() {
        var action = $(this).val();
        $('#gradeField').toggle(action === 'reusable');
        $('#valueField').toggle(action === 'sell');
    });
</script>
@stop
