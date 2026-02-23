@extends('adminlte::page')

@section('title', __('general_content.leads_trans_key'))

@section('content_header')
  <div class="row mb-2">
    <h1>{{ __('general_content.leads_trans_key')}}</h1>
  </div>
@stop

@section('right-sidebar')

@section('content')
<div class="card">
  <div class="card-header p-2">
    <ul class="nav nav-pills">
      <li class="nav-item"><a class="nav-link active" href="#Dashboard" data-toggle="tab">{{ __('general_content.dashboard_trans_key') }}</a></li> 
      <li class="nav-item"><a class="nav-link" href="#List" data-toggle="tab">{{ __('general_content.list_leads_trans_key') }}</a></li> 
    </ul>
  </div>
  <!-- /.card-header -->
  <div class="tab-content p-3">
    <div class="tab-pane active" id="Dashboard">
      <div class="row">
        <div class="col-md-3">
          <x-adminlte-card title="{{ __('general_content.statistiques_trans_key') }}" theme="teal" icon="fas fa-chart-bar text-white" collapsible removable maximizable>
            <canvas id="donutChart" width="400" height="400"></canvas>
          </x-adminlte-card>
        </div>
        <div class="col-md-3">
          <x-adminlte-small-box title="{{ __('general_content.lead_count_trans_key') }}" text="{{ $leadsCount }}" icon="fas fa-chart-bar text-white"
            theme="purple"/>
        </div>
        <div class="col-md-3">
          <x-adminlte-card title="{{ __('general_content.statistiques_trans_key') }}" theme="orange" icon="fas fa-users text-white" collapsible removable maximizable>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>{{ __('general_content.user_trans_key') }}</th>
                        <th>{{ __('general_content.new_trans_key') }}</th>
                        <th>{{ __('general_content.assigned_trans_key') }}</th>
                        <th>{{ __('general_content.in_progress_trans_key') }}</th>
                        <th>{{ __('general_content.converted_trans_key') }}</th>
                        <th>{{ __('general_content.lost_trans_key') }}</th>
                    </tr>
                </thead>
                <tbody>
                  @foreach ($leadsCountByUser as $userId => $leads)
                  <tr>
                    <td>{{ $leads->first()->UserManagement->name ?? 'N/A' }}</td>
                      @for ($i = 1; $i <= 5; $i++)
                          <td>
                              {{ $leads->where('statu', $i)->sum('total') ?? 0 }}
                              <!-- Shows 0 if no leads for this user with this status -->
                          </td>
                      @endfor
                  </tr>
                  @endforeach
                </tbody>
            </table>
          </x-adminlte-card>
        </div>
        
        <div class="col-md-3">
          <x-adminlte-card title="{{ __('general_content.statistiques_trans_key') }}" theme="warning" icon="fas fa-chart-bar text-white" collapsible removable maximizable>
            <canvas id="priorityChart" width="400" height="400"></canvas>
          </x-adminlte-card>
        </div>
      </div>
    </div>
    <div class="tab-pane" id="List">
      @livewire('leads-index')
    </div>
  </div>
  <!-- /.card -->
</div>
@stop

@section('css')
@stop

@section('js')
<script src="https://cdn.jsdelivr.net/gh/livewire/sortable@v1.x.x/dist/livewire-sortable.js"></script>

<script>
//-------------
//- PIE CHART -
//-------------
  var donutChartCanvas = $('#donutChart').get(0).getContext('2d')
  var donutData        = {
      labels: [
        @foreach ($data['leadsCountRate'] as $item)
              @if(1 == $item->statu )  "{{ __('general_content.new_trans_key') }}", @endif
              @if(2 == $item->statu )  "{{ __('general_content.assigned_trans_key') }}", @endif
              @if(3 == $item->statu )  "{{ __('general_content.in_progress_trans_key') }}", @endif
              @if(4 == $item->statu )  "{{ __('general_content.converted_trans_key') }}", @endif
              @if(5 == $item->statu )  "{{ __('general_content.lost_trans_key') }}", @endif
        @endforeach
      ],
      datasets: [
        {
          data: [
                @foreach ($data['leadsCountRate'] as $item)
                "{{ $item->leadsCountRate }}",
                @endforeach
              ], 
              backgroundColor: [
                  'rgba(23, 162, 184, 1)',
                  'rgba(255, 193, 7, 1)',
                  'rgba(40, 167, 69, 1)',
                  'rgba(220, 53, 69, 1)',
                  'rgba(108, 117, 125, 1)',
                  'rgba(0, 123, 255, 1)',
              ],
        }
      ]
    }
    var donutOptions     = {
      maintainAspectRatio : false,
      responsive : true,
    }
    //Create pie or douhnut chart
    // You can switch between pie and douhnut using the method below.
    new Chart(donutChartCanvas, {
      type: 'pie',
      data: donutData,
      options: donutOptions
    })


    var ctx = document.getElementById('priorityChart').getContext('2d');
var priorityChart = new Chart(ctx, {
    type: 'pie',
    data: {
        labels: [
            @foreach ($leadsCountByPriority as $item)
                @if(1 == $item->priority) "{{ __('general_content.burning_trans_key') }}", @endif
                @if(2 == $item->priority) "{{ __('general_content.hot_trans_key') }}", @endif
                @if(3 == $item->priority) "{{ __('general_content.lukewarm_trans_key') }}", @endif
                @if(4 == $item->priority) "{{ __('general_content.cold_trans_key') }}", @endif
            @endforeach
        ],
        datasets: [
            {
                data: [
                    @foreach ($leadsCountByPriority as $item)
                        {{ $item->leadsCount }},
                    @endforeach
                ],
                backgroundColor: [
                    'rgba(220, 53, 69, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(40, 167, 69, 1)',
                    'rgba(0, 123, 255, 1)',
                ],
            }
        ]
    },
    options: {
        maintainAspectRatio: false,
        responsive: true,
    }
});
  </script>
@stop