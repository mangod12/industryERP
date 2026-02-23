@extends('adminlte::page')

@section('title', 'Scrap Analytics')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-chart-pie text-purple"></i> Scrap Analytics</h1>
    </div>
    <div class="col-sm-6">
        <div class="float-sm-right">
            <form method="GET" class="form-inline">
                <select name="period" class="form-control mr-2" onchange="this.form.submit()">
                    <option value="week" {{ request('period', 'month') == 'week' ? 'selected' : '' }}>This Week</option>
                    <option value="month" {{ request('period', 'month') == 'month' ? 'selected' : '' }}>This Month</option>
                    <option value="quarter" {{ request('period') == 'quarter' ? 'selected' : '' }}>This Quarter</option>
                    <option value="year" {{ request('period') == 'year' ? 'selected' : '' }}>This Year</option>
                </select>
                <a href="{{ route('scrap.export') }}" class="btn btn-outline-success">
                    <i class="fas fa-file-excel"></i> Export
                </a>
            </form>
        </div>
    </div>
</div>
@stop

@section('content')
<!-- Key Metrics -->
<div class="row">
    <div class="col-lg-3 col-6">
        <div class="info-box">
            <span class="info-box-icon bg-warning"><i class="fas fa-weight-hanging"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Total Scrap Weight</span>
                <span class="info-box-number">{{ number_format($data['total_weight'], 1) }} <small>kg</small></span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box">
            <span class="info-box-icon bg-danger"><i class="fas fa-percentage"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Scrap Rate</span>
                <span class="info-box-number">{{ number_format($data['scrap_rate'], 2) }}%</span>
                <span class="text-{{ $data['scrap_rate'] < config('steel.analytics.scrap_threshold', 5) ? 'success' : 'danger' }}">
                    <i class="fas fa-{{ $data['scrap_rate'] < config('steel.analytics.scrap_threshold', 5) ? 'arrow-down' : 'arrow-up' }}"></i>
                    Target: < {{ config('steel.analytics.scrap_threshold', 5) }}%
                </span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box">
            <span class="info-box-icon bg-success"><i class="fas fa-rupee-sign"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Value Recovered</span>
                <span class="info-box-number">₹{{ number_format($data['value_recovered'], 0) }}</span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box">
            <span class="info-box-icon bg-info"><i class="fas fa-recycle"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Recovery Rate</span>
                <span class="info-box-number">{{ number_format($data['recovery_rate'], 1) }}%</span>
                <span class="text-muted">Returned + Sold</span>
            </div>
        </div>
    </div>
</div>

<!-- Charts Row -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-pie"></i> Scrap by Material Type</h3>
            </div>
            <div class="card-body">
                <canvas id="materialChart" height="250"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-bar"></i> Scrap by Reason</h3>
            </div>
            <div class="card-body">
                <canvas id="reasonChart" height="250"></canvas>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-line"></i> Scrap Trend</h3>
            </div>
            <div class="card-body">
                <canvas id="trendChart" height="200"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-doughnut"></i> Status Distribution</h3>
            </div>
            <div class="card-body">
                <canvas id="statusChart" height="250"></canvas>
            </div>
        </div>
    </div>
</div>

<!-- Top Scrap Materials Table -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-list-ol"></i> Top Scrap Materials</h3>
            </div>
            <div class="card-body p-0">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Material</th>
                            <th class="text-right">Weight (kg)</th>
                            <th class="text-right">Count</th>
                            <th>% of Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($data['by_material'] as $material)
                        <tr>
                            <td>{{ $material->material_name }}</td>
                            <td class="text-right">{{ number_format($material->total_weight, 1) }}</td>
                            <td class="text-right">{{ $material->count }}</td>
                            <td>
                                <div class="progress progress-sm">
                                    <div class="progress-bar bg-warning" style="width: {{ $data['total_weight'] > 0 ? ($material->total_weight / $data['total_weight'] * 100) : 0 }}%"></div>
                                </div>
                                {{ $data['total_weight'] > 0 ? number_format($material->total_weight / $data['total_weight'] * 100, 1) : 0 }}%
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="4" class="text-center text-muted">No data available</td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-industry"></i> Scrap by Production Stage</h3>
            </div>
            <div class="card-body p-0">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Stage</th>
                            <th class="text-right">Weight (kg)</th>
                            <th class="text-right">Count</th>
                            <th>% of Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($data['by_stage'] as $stage)
                        <tr>
                            <td>
                                @switch($stage->stage)
                                    @case('fabrication')
                                        <span class="badge badge-info">Fabrication</span>
                                        @break
                                    @case('painting')
                                        <span class="badge badge-warning">Painting</span>
                                        @break
                                    @case('dispatch')
                                        <span class="badge badge-success">Dispatch</span>
                                        @break
                                    @default
                                        <span class="badge badge-secondary">{{ $stage->stage ?? 'Unknown' }}</span>
                                @endswitch
                            </td>
                            <td class="text-right">{{ number_format($stage->total_weight, 1) }}</td>
                            <td class="text-right">{{ $stage->count }}</td>
                            <td>
                                <div class="progress progress-sm">
                                    <div class="progress-bar bg-info" style="width: {{ $data['total_weight'] > 0 ? ($stage->total_weight / $data['total_weight'] * 100) : 0 }}%"></div>
                                </div>
                                {{ $data['total_weight'] > 0 ? number_format($stage->total_weight / $data['total_weight'] * 100, 1) : 0 }}%
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="4" class="text-center text-muted">No data available</td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Insights & Recommendations -->
<div class="card card-outline card-purple">
    <div class="card-header">
        <h3 class="card-title"><i class="fas fa-lightbulb"></i> Insights & Recommendations</h3>
    </div>
    <div class="card-body">
        <div class="row">
            @if($data['scrap_rate'] > config('steel.analytics.scrap_threshold', 5))
            <div class="col-md-4">
                <div class="alert alert-danger">
                    <h5><i class="fas fa-exclamation-triangle"></i> High Scrap Rate</h5>
                    <p>Current scrap rate ({{ number_format($data['scrap_rate'], 2) }}%) exceeds the target threshold of {{ config('steel.analytics.scrap_threshold', 5) }}%.</p>
                    <small>Investigate cutting patterns and material handling procedures.</small>
                </div>
            </div>
            @endif

            @if(($data['by_reason'][0]->reason_code ?? '') == 'cutting_waste')
            <div class="col-md-4">
                <div class="alert alert-warning">
                    <h5><i class="fas fa-cut"></i> Cutting Waste Dominant</h5>
                    <p>Cutting waste is the leading cause of scrap.</p>
                    <small>Consider optimizing nesting layouts and using remnant tracking.</small>
                </div>
            </div>
            @endif

            @if($data['recovery_rate'] < config('steel.analytics.reusability_target', 70))
            <div class="col-md-4">
                <div class="alert alert-info">
                    <h5><i class="fas fa-recycle"></i> Recovery Opportunity</h5>
                    <p>Current recovery rate is {{ number_format($data['recovery_rate'], 1) }}%.</p>
                    <small>Review pending scrap for reusable pieces before disposal.</small>
                </div>
            </div>
            @endif

            @if($data['pending_count'] > 50)
            <div class="col-md-4">
                <div class="alert alert-warning">
                    <h5><i class="fas fa-clock"></i> Pending Review Backlog</h5>
                    <p>{{ $data['pending_count'] }} items pending review.</p>
                    <small>Process pending scrap to maintain accurate inventory.</small>
                </div>
            </div>
            @endif
        </div>
    </div>
</div>
@stop

@section('css')
<style>
    .info-box-number { font-size: 1.5rem; }
    .progress-sm { height: 10px; }
</style>
@stop

@section('js')
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    // Material Pie Chart
    new Chart(document.getElementById('materialChart').getContext('2d'), {
        type: 'pie',
        data: {
            labels: {!! json_encode($data['by_material']->pluck('material_name')) !!},
            datasets: [{
                data: {!! json_encode($data['by_material']->pluck('total_weight')) !!},
                backgroundColor: ['#ffc107', '#dc3545', '#17a2b8', '#28a745', '#6c757d', '#007bff', '#fd7e14', '#6f42c1']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'right' } } }
    });

    // Reason Bar Chart
    new Chart(document.getElementById('reasonChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: {!! json_encode($data['by_reason']->pluck('reason_code')->map(fn($r) => config('steel.scrap_reason_codes.'.$r, $r))) !!},
            datasets: [{
                label: 'Weight (kg)',
                data: {!! json_encode($data['by_reason']->pluck('total_weight')) !!},
                backgroundColor: '#ffc107'
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    // Trend Line Chart
    new Chart(document.getElementById('trendChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: {!! json_encode($data['trend']->pluck('date')) !!},
            datasets: [{
                label: 'Scrap Weight (kg)',
                data: {!! json_encode($data['trend']->pluck('total_weight')) !!},
                borderColor: '#ffc107',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    // Status Doughnut Chart
    new Chart(document.getElementById('statusChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: {!! json_encode($data['by_status']->pluck('status')->map(fn($s) => ucfirst(str_replace('_', ' ', $s)))) !!},
            datasets: [{
                data: {!! json_encode($data['by_status']->pluck('count')) !!},
                backgroundColor: ['#ffc107', '#28a745', '#17a2b8', '#dc3545', '#007bff']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
</script>
@stop
