@extends('adminlte::page')

@section('title', __('general_content.estimated_budget_trans_key'))

@section('content_header')
    <h1>{{ __('general_content.estimated_budget_trans_key') }}</h1>
@stop

@section('content')
    <x-InfocalloutComponent note="Used for dashboard chart."  />
    @livewire('estimated-budget')
@stop

@section('css')
@stop

@section('js')
@stop