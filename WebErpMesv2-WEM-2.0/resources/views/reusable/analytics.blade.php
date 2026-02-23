@extends('adminlte::page')

@section('title', 'Reusable Stock Analytics')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-chart-bar text-purple"></i> Reusable Stock Analytics</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('reusable.index') }}">Reusable Stock</a></li>
            <li class="breadcrumb-item active">Analytics</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<!-- Key Metrics -->
<div class="row">
    <div class="col-lg-3 col-6">
        <div class="info-box bg-info">
            <span class="info-box-icon"><i class="fas fa-boxes"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Available Stock</span>
                <span class="info-box-number">{{ number_format($data['available_weight'], 1) }} kg</span>
                <span class="progress-description">{{ $data['available_count'] }} items</span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box bg-success">
            <span class="info-box-icon"><i class="fas fa-check-circle"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Utilization Rate</span>
                <span class="info-box-number">{{ number_format($data['utilization_rate'], 1) }}%</span>
                <span class="progress-description">Used from stock</span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box bg-warning">
            <span class="info-box-icon"><i class="fas fa-clock"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Avg. Stock Age</span>
                <span class="info-box-number">{{ number_format($data['avg_age_days'], 0) }} days</span>
                <span class="progress-description">Available items</span>
            </div>
        </div>
    </div>
    <div class="col-lg-3 col-6">
        <div class="info-box bg-primary">
            <span class="info-box-icon"><i class="fas fa-rupee-sign"></i></span>
            <div class="info-box-content">
                <span class="info-box-text">Value Saved</span>
                <span class="info-box-number">₹{{ number_format($data['value_saved'], 0) }}</span>
                <span class="progress-description">By reusing stock</span>
            </div>
        </div>
    </div>
</div>

<!-- Charts -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-pie"></i> Stock by Material</h3>
            </div>
            <div class="card-body">
                <canvas id="materialChart" height="250"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-doughnut"></i> Grade Distribution</h3>
            </div>
            <div class="card-body">
                <canvas id="gradeChart" height="250"></canvas>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-line"></i> Usage Trend</h3>
            </div>
            <div class="card-body">
                <canvas id="trendChart" height="200"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-chart-bar"></i> Status Breakdown</h3>
            </div>
            <div class="card-body">
                <canvas id="statusChart" height="250"></canvas>
            </div>
        </div>
    </div>
</div>

<!-- Detailed Tables -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-sort-amount-down"></i> Top Materials in Stock</h3>
            </div>
            <div class="card-body p-0">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Material</th>
                            <th class="text-right">Weight (kg)</th>
                            <th class="text-right">Items</th>
                            <th>Distribution</th>
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
                                    <div class="progress-bar bg-info" 
                                         style="width: {{ $data['available_weight'] > 0 ? ($material->total_weight / $data['available_weight'] * 100) : 0 }}%">
                                    </div>
                                </div>
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="4" class="text-center text-muted">No data</td>
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
                <h3 class="card-title"><i class="fas fa-calendar-alt"></i> Aging Analysis</h3>
            </div>
            <div class="card-body p-0">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Age Range</th>
                            <th class="text-right">Items</th>
                            <th class="text-right">Weight (kg)</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($data['aging'] as $age)
                        <tr>
                            <td>{{ $age['label'] }}</td>
                            <td class="text-right">{{ $age['count'] }}</td>
                            <td class="text-right">{{ number_format($age['weight'], 1) }}</td>
                            <td>
                                @if($age['days'] < 30)
                                    <span class="badge badge-success">Fresh</span>
                                @elseif($age['days'] < 90)
                                    <span class="badge badge-warning">Aging</span>
                                @else
                                    <span class="badge badge-danger">Old Stock</span>
                                @endif
                            </td>
                        </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Insights -->
<div class="card card-outline card-purple">
    <div class="card-header">
        <h3 class="card-title"><i class="fas fa-lightbulb"></i> Insights & Recommendations</h3>
    </div>
    <div class="card-body">
        <div class="row">
            @if($data['utilization_rate'] < config('steel.analytics.reusability_target', 70))
            <div class="col-md-4">
                <div class="alert alert-warning">
                    <h5><i class="fas fa-chart-line"></i> Low Utilization</h5>
                    <p>Current utilization ({{ number_format($data['utilization_rate'], 1) }}%) is below target.</p>
                    <small>Encourage operators to check reusable stock before using new materials.</small>
                </div>
            </div>
            @endif

            @if(($data['aging'][2]['count'] ?? 0) > 10)
            <div class="col-md-4">
                <div class="alert alert-danger">
                    <h5><i class="fas fa-hourglass-half"></i> Aging Stock</h5>
                    <p>{{ $data['aging'][2]['count'] ?? 0 }} items are older than 90 days.</p>
                    <small>Review old stock for possible disposal or reclassification.</small>
                </div>
            </div>
            @endif

            @if(($data['by_grade']['C'] ?? 0) > ($data['available_count'] * 0.3))
            <div class="col-md-4">
                <div class="alert alert-info">
                    <h5><i class="fas fa-exclamation-circle"></i> High Grade C Stock</h5>
                    <p>Over 30% of stock is Grade C.</p>
                    <small>Consider disposing of low-grade stock to free up space.</small>
                </div>
            </div>
            @endif

            @if($data['utilization_rate'] >= config('steel.analytics.reusability_target', 70))
            <div class="col-md-4">
                <div class="alert alert-success">
                    <h5><i class="fas fa-thumbs-up"></i> Good Performance</h5>
                    <p>Utilization rate meets or exceeds target!</p>
                    <small>Continue current practices for optimal material efficiency.</small>
                </div>
            </div>
            @endif
        </div>
    </div>
</div>
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
                backgroundColor: ['#17a2b8', '#28a745', '#ffc107', '#dc3545', '#6c757d', '#007bff', '#fd7e14', '#6f42c1']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'right' } } }
    });

    // Grade Doughnut Chart
    new Chart(document.getElementById('gradeChart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Grade A', 'Grade B', 'Grade C'],
            datasets: [{
                data: [
                    {{ $data['by_grade']['A'] ?? 0 }},
                    {{ $data['by_grade']['B'] ?? 0 }},
                    {{ $data['by_grade']['C'] ?? 0 }}
                ],
                backgroundColor: ['#28a745', '#ffc107', '#dc3545']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });

    // Trend Line Chart
    new Chart(document.getElementById('trendChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: {!! json_encode($data['trend']->pluck('date')) !!},
            datasets: [
                {
                    label: 'Added (kg)',
                    data: {!! json_encode($data['trend']->pluck('added')) !!},
                    borderColor: '#17a2b8',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Used (kg)',
                    data: {!! json_encode($data['trend']->pluck('used')) !!},
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    // Status Bar Chart
    new Chart(document.getElementById('statusChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Available', 'Reserved', 'Used'],
            datasets: [{
                label: 'Items',
                data: [
                    {{ $data['by_status']['available'] ?? 0 }},
                    {{ $data['by_status']['reserved'] ?? 0 }},
                    {{ $data['by_status']['used'] ?? 0 }}
                ],
                backgroundColor: ['#28a745', '#ffc107', '#6c757d']
            }]
        },
        options: { 
            responsive: true, 
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });
</script>
@stop
