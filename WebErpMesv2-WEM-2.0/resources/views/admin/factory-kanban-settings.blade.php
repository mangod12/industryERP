@extends('adminlte::page')

@section('title', __('general_content.workflow_settings_trans_key'))

@section('content_header')
    <h1>{{ __('general_content.workflow_settings_trans_key') }}</h1>
@stop

@section('content')
    <x-InfocalloutComponent note="{{__('general_content.kanban_setting_note_trans_key') }}"  />
    <x-adminlte-card theme="lime" theme-mode="outline">
        @livewire('kanban-setting')
    </x-adminlte-card>
@stop

@section('css')
@stop

@section('js')
@stop