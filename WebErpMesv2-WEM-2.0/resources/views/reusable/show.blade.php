@extends('adminlte::page')

@section('title', 'Reusable Stock Details')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-boxes text-info"></i> Reusable Stock #{{ $item->id }}</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('reusable.index') }}">Reusable Stock</a></li>
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
                @switch($item->quality_grade)
                    @case('A') bg-success @break
                    @case('B') bg-warning @break
                    @case('C') bg-danger @break
                @endswitch
            ">
                <h3 class="card-title">
                    {{ $item->material_name }}
                    <span class="badge badge-light ml-2">Grade {{ $item->quality_grade }}</span>
                    <span class="badge badge-{{ $item->status == 'available' ? 'success' : ($item->status == 'reserved' ? 'warning' : 'secondary') }} ml-1">
                        {{ ucfirst($item->status) }}
                    </span>
                </h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Dimensions & Weight</h5>
                        <table class="table table-sm table-borderless">
                            <tr>
                                <th width="40%">Material:</th>
                                <td><strong>{{ $item->material_name }}</strong></td>
                            </tr>
                            <tr>
                                <th>Length:</th>
                                <td>{{ number_format($item->length_mm, 1) }} mm</td>
                            </tr>
                            <tr>
                                <th>Width:</th>
                                <td>{{ number_format($item->width_mm, 1) }} mm</td>
                            </tr>
                            <tr>
                                <th>Thickness:</th>
                                <td>{{ $item->thickness_mm ? number_format($item->thickness_mm, 1) . ' mm' : 'Not specified' }}</td>
                            </tr>
                            <tr>
                                <th>Weight:</th>
                                <td><strong>{{ number_format($item->weight_kg, 2) }} kg</strong></td>
                            </tr>
                            <tr>
                                <th>Quantity:</th>
                                <td>{{ $item->quantity }} pcs</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h5>Stock Information</h5>
                        <table class="table table-sm table-borderless">
                            <tr>
                                <th width="40%">Quality Grade:</th>
                                <td>
                                    <span class="badge badge-{{ $item->quality_grade == 'A' ? 'success' : ($item->quality_grade == 'B' ? 'warning' : 'danger') }} badge-lg">
                                        Grade {{ $item->quality_grade }}
                                        @switch($item->quality_grade)
                                            @case('A') - Excellent @break
                                            @case('B') - Minor defects @break
                                            @case('C') - Use with caution @break
                                        @endswitch
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <th>Status:</th>
                                <td>
                                    @switch($item->status)
                                        @case('available')
                                            <span class="badge badge-success badge-lg">✓ Available for Use</span>
                                            @break
                                        @case('reserved')
                                            <span class="badge badge-warning badge-lg">⏳ Reserved</span>
                                            @break
                                        @case('used')
                                            <span class="badge badge-secondary badge-lg">✓ Used</span>
                                            @break
                                    @endswitch
                                </td>
                            </tr>
                            <tr>
                                <th>Location:</th>
                                <td>{{ $item->location ?? 'Not specified' }}</td>
                            </tr>
                            <tr>
                                <th>Added:</th>
                                <td>{{ $item->created_at->format('d M Y, h:i A') }}</td>
                            </tr>
                            @if($item->used_at)
                            <tr>
                                <th>Used On:</th>
                                <td>{{ $item->used_at->format('d M Y, h:i A') }}</td>
                            </tr>
                            @endif
                            @if($item->times_considered)
                            <tr>
                                <th>Times Considered:</th>
                                <td>{{ $item->times_considered }}</td>
                            </tr>
                            @endif
                        </table>
                    </div>
                </div>

                @if($item->notes)
                <hr>
                <h5>Notes</h5>
                <p class="bg-light p-3 rounded">{{ $item->notes }}</p>
                @endif

                @if($item->scrapRecord)
                <hr>
                <h5>Origin (From Scrap)</h5>
                <div class="callout callout-info">
                    <p class="mb-1">
                        <i class="fas fa-recycle"></i> 
                        Originally from Scrap Record 
                        <a href="{{ route('scrap.show', $item->scrapRecord) }}">#{{ $item->scrap_record_id }}</a>
                    </p>
                    <small class="text-muted">
                        {{ $item->scrapRecord->material_name }} - 
                        {{ $item->scrapRecord->reason_label }} - 
                        {{ $item->scrapRecord->created_at->format('d M Y') }}
                    </small>
                </div>
                @endif
            </div>
        </div>

        <!-- Usage History (if used) -->
        @if($item->status == 'used')
        <div class="card card-outline card-secondary">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-history"></i> Usage History</h3>
            </div>
            <div class="card-body">
                <ul class="timeline">
                    <li class="time-label">
                        <span class="bg-info">{{ $item->created_at->format('d M Y') }}</span>
                    </li>
                    <li>
                        <i class="fas fa-plus bg-success"></i>
                        <div class="timeline-item">
                            <span class="time"><i class="far fa-clock"></i> {{ $item->created_at->format('h:i A') }}</span>
                            <h3 class="timeline-header">Added to Reusable Stock</h3>
                        </div>
                    </li>
                    @if($item->used_at)
                    <li class="time-label">
                        <span class="bg-success">{{ $item->used_at->format('d M Y') }}</span>
                    </li>
                    <li>
                        <i class="fas fa-industry bg-primary"></i>
                        <div class="timeline-item">
                            <span class="time"><i class="far fa-clock"></i> {{ $item->used_at->format('h:i A') }}</span>
                            <h3 class="timeline-header">Used in Production</h3>
                            @if($item->used_for_work_order)
                            <div class="timeline-body">Work Order: {{ $item->used_for_work_order }}</div>
                            @endif
                        </div>
                    </li>
                    @endif
                    <li>
                        <i class="far fa-clock bg-gray"></i>
                    </li>
                </ul>
            </div>
        </div>
        @endif
    </div>

    <!-- Action Panel -->
    <div class="col-md-4">
        @if($item->status == 'available')
        <div class="card card-success">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-cogs"></i> Actions</h3>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ route('reusable.mark-used', $item) }}">
                    @csrf
                    <div class="form-group">
                        <label>Work Order (optional)</label>
                        <input type="text" name="work_order_id" class="form-control" placeholder="Enter work order ID">
                    </div>
                    <button type="submit" class="btn btn-success btn-block mb-2">
                        <i class="fas fa-check"></i> Mark as Used
                    </button>
                </form>

                <hr>

                <form method="POST" action="{{ route('reusable.return-inventory', $item) }}">
                    @csrf
                    <button type="submit" class="btn btn-primary btn-block mb-2" 
                            onclick="return confirm('Return to main inventory?')">
                        <i class="fas fa-undo"></i> Return to Inventory
                    </button>
                </form>

                <form method="POST" action="{{ route('reusable.mark-scrap', $item) }}">
                    @csrf
                    <button type="submit" class="btn btn-warning btn-block" 
                            onclick="return confirm('Move back to scrap?')">
                        <i class="fas fa-recycle"></i> Send to Scrap
                    </button>
                </form>
            </div>
        </div>

        <!-- Update Grade -->
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-star"></i> Update Grade</h3>
            </div>
            <form method="POST" action="{{ route('reusable.update-grade', $item) }}">
                @csrf
                <div class="card-body">
                    <div class="form-group mb-0">
                        <select name="quality_grade" class="form-control">
                            <option value="A" {{ $item->quality_grade == 'A' ? 'selected' : '' }}>Grade A - Excellent</option>
                            <option value="B" {{ $item->quality_grade == 'B' ? 'selected' : '' }}>Grade B - Minor defects</option>
                            <option value="C" {{ $item->quality_grade == 'C' ? 'selected' : '' }}>Grade C - Use with caution</option>
                        </select>
                    </div>
                </div>
                <div class="card-footer">
                    <button type="submit" class="btn btn-secondary btn-sm btn-block">Update Grade</button>
                </div>
            </form>
        </div>
        @elseif($item->status == 'reserved')
        <div class="card card-warning">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-lock"></i> Reserved</h3>
            </div>
            <div class="card-body">
                <p class="text-muted">This item is currently reserved.</p>
                <form method="POST" action="{{ route('reusable.return-available', $item) }}">
                    @csrf
                    <button type="submit" class="btn btn-primary btn-block">
                        <i class="fas fa-unlock"></i> Release Reservation
                    </button>
                </form>
            </div>
        </div>
        @else
        <div class="card">
            <div class="card-body text-center">
                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                <h5>Already Used</h5>
                <p class="text-muted">This stock has been used in production.</p>
            </div>
        </div>
        @endif

        <!-- Similar Items -->
        @if(isset($similarItems) && $similarItems->count() > 0)
        <div class="card card-outline card-info">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-clone"></i> Similar Items</h3>
            </div>
            <div class="card-body p-0">
                <ul class="list-group list-group-flush">
                    @foreach($similarItems as $similar)
                    <li class="list-group-item">
                        <a href="{{ route('reusable.show', $similar) }}">
                            #{{ $similar->id }} - {{ $similar->length_mm }}×{{ $similar->width_mm }}mm
                        </a>
                        <span class="badge badge-{{ $similar->quality_grade == 'A' ? 'success' : ($similar->quality_grade == 'B' ? 'warning' : 'danger') }} float-right">
                            {{ $similar->quality_grade }}
                        </span>
                    </li>
                    @endforeach
                </ul>
            </div>
        </div>
        @endif

        <a href="{{ route('reusable.index') }}" class="btn btn-secondary btn-block">
            <i class="fas fa-arrow-left"></i> Back to List
        </a>
    </div>
</div>
@stop
