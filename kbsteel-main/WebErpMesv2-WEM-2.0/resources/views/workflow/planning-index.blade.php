@extends('adminlte::page')

@section('title', __('general_content.load_planning_trans_key'))

@section('content_header')
  <link rel="stylesheet" href="{{ asset('css/custom.css') }}">
    <div class="row mb-2">
      <div class="col-sm-8">
        <h1>{{__('general_content.load_planning_trans_key') }}</h1>
      </div>
      <div class="col-sm-2">
        <!-- Button Modal -->
        <button type="button" class="btn btn-primary float-sm-right" data-toggle="modal" data-target="#taskCalculationRessource">
          {{__('general_content.gantt_info_2_trans_key') }}   ({{ $countTaskNullRessource }})
        </button>
      </div>
      <div class="col-sm-2">
        <!-- Button Modal -->
        <button type="button" class="btn btn-primary float-sm-right" data-toggle="modal" data-target="#taskCalculationDate">
          {{__('general_content.gantt_info_1_trans_key') }}  ({{ $countTaskNullDate }})
        </button>
      </div>
    </div>
@stop

@section('right-sidebar')

@section('content')
  @livewire('task-calculation-date')

  <x-adminlte-alert theme="info" title="Info">
    {{__('general_content.load_planning_info_1_trans_key') }}
  </x-adminlte-alert>

  <x-adminlte-card theme="lime" theme-mode="outline">
    @include('include.alert-result')
    <form action="{{ route('production.load.planning') }}" method="GET">
      <div class="row">
        <div class="form-group col-2">
          <label for="start_date">{{ __('general_content.start_date_trans_key') }} :</label>
          <input type="date" class="form-control" id="start_date" name="start_date" required value="{{ $startDate ?? '' }}">
        </div>
        <div class="form-group col-2">
          <label for="end_date">{{ __('general_content.end_date_trans_key') }}</label>
          <input type="date" class="form-control" name="end_date"  id="end_date" required value="{{ $endDate ?? '' }}">
        </div>
        <div class="form-group col-2">
          <label for="display_hours_diff">{{ __('general_content.display_hours_diff_trans_key') }}</label>
          <x-adminlte-input-switch name="display_hours_diff" 
            data-on-text="{{ __('general_content.yes_trans_key') }}" 
            data-off-text="{{ __('general_content.no_trans_key') }}"
            data-on-color="teal" 
            data-off-color="danger" 
            is-checked="{{ $displayHoursDiff }}" />
        </div>
        <div class="form-group col-2">
          <x-adminlte-button class="btn-flat" type="submit" label="{{ __('general_content.submit_trans_key') }}" theme="danger" icon="fas fa-lg fa-save"/>
        </div>
      </div>
    </form>
  </x-adminlte-card>

  <x-adminlte-card theme="lime" theme-mode="outline">
    <div class="table-responsive">
      <table id="tblDemo" class="table table-hover table-bordered align-middle shadow-sm rounded w-100">

          <thead class="bg-primary text-white text-center">
            <tr>
                <th></th>
                <th>{{ __('general_content.service_trans_key') }}</th>
                @foreach ($possibleDates as $singleDay)
                    @php
                        $isWeekend = date('N', strtotime($singleDay)) >= 6;
                        $isBankHoliday = in_array(Carbon\Carbon::parse($singleDay)->toDateString(), $bankHolidays);
                        
                        // Définir la classe CSS pour le jour
                        $dayClass = match (true) {
                            $isBankHoliday => 'bg-dark text-white', // Jours OFF -> Fond foncé
                            $isWeekend => 'bg-info-subtle text-dark', // Week-end -> Fond bleu pâle
                            default => 'bg-light', // Jour normal
                        };
                    @endphp
                    <th class="fw-normal {{ $dayClass }}">{{ $singleDay }}</th>
                @endforeach
            </tr>
        </thead>
          <tbody>
              @foreach ($services as $service)
                  <tr class="align-middle">
                      <!-- Avatar -->
                      <td class="text-center">
                          @if ($service->picture)
                              <img alt="{{ $service->label }}" class="rounded-circle border shadow-sm"
                                  src="{{ asset('/images/methods/' . $service->picture) }}" width="40" height="40">
                          @endif
                      </td>
                      
                      <!-- Nom du service -->
                      <td class="fw-semibold">{{ $service->label }}</td>
                      
                      <!-- Boucle des jours -->
                      @foreach ($possibleDates as $singleDay)
                          @php
                              $isWeekend = date('N', strtotime($singleDay)) >= 6;
                              $isBankHoliday = in_array(Carbon\Carbon::parse($singleDay)->toDateString(), $bankHolidays);
                              
                              // Liste des tâches associées à ce jour
                              $tasksList = $tasksPerServiceDay[$service->id][$singleDay] ?? [];
                              $tooltipContent = implode(', ', array_map(fn($tache) => '#' . $tache, $tasksList));

                              $loadPercentage = $structureRateLoad[$singleDay][$service->id] ?? null;
                              $hoursDiff = $loadPercentage ? round(16 - ($loadPercentage / 100) * 16, 2) : null;

                              // Définition des couleurs de fond
                              $bgColor = match (true) {
                                  $isBankHoliday => 'bg-dark text-white', // Jours OFF (feriés)
                                  is_null($loadPercentage) => $isWeekend ? 'bg-info-subtle' : 'bg-light',
                                  $displayHoursDiff && $hoursDiff <= 0 => 'bg-success text-white',
                                  $displayHoursDiff && $hoursDiff <= 4 => 'bg-warning text-dark',
                                  $displayHoursDiff && $hoursDiff <= 8 => 'bg-orange text-white',
                                  $displayHoursDiff && $hoursDiff <= 12 => 'bg-danger-light text-white',
                                  $displayHoursDiff => 'bg-dark text-white',
                                  $loadPercentage >= 100 => 'bg-danger text-white',
                                  $loadPercentage >= 80 => 'bg-danger-light',
                                  $loadPercentage >= 50 => 'bg-orange text-white',
                                  $loadPercentage >= 20 => 'bg-warning text-dark',
                                  default => 'bg-success text-white',
                              };

                              // Texte affiché dans la cellule
                              $displayValue = match (true) {
                                  $isBankHoliday => '<span class="text-white fw-bold">OFF</span>',
                                  $isWeekend => '<span class="text-muted">Weekend</span>',
                                  is_null($loadPercentage) => '<span class="text-muted">N/A</span>',
                                  $displayHoursDiff && $hoursDiff <= 0 => "<i class='bi bi-arrow-up-circle-fill'></i> + " . abs($hoursDiff) . " h",
                                  $displayHoursDiff => "<i class='bi bi-arrow-down-circle-fill'></i> - " . $hoursDiff . " h",
                                  default => $loadPercentage . '%',
                              };
                          @endphp

                          <td class="text-center fw-bold {{ $bgColor }} rounded-pill p-2 shadow-sm"
                              data-bs-toggle="tooltip" data-bs-placement="top" title="{{ $tooltipContent }}">
                              {!! $displayValue !!}
                          </td>
                      @endforeach

                  </tr>
              @endforeach
          </tbody>
      </table>
    </div>
    <div class="card-footer">
      <a href="{{ url()->previous() }}" class="btn btn-secondary"><i class="fas fa-arrow-left"></i> {{ __('general_content.back_trans_key') }}</a>
    </div>
  </x-adminlte-card>
@stop

@section('css')
@stop

@section('js')
  
<script>
    document.addEventListener("DOMContentLoaded", function () {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    });
</script>
@stop

