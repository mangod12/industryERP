@extends('adminlte::page')

@section('title', __('general_content.email_trans_key'))

@section('content_header')
<h1>{{ __('general_content.email_trans_key') }}</h1>
@stop

@section('content')

    <!-- Formulaire de composition -->

    <form action="{{ route('email.send', ['type' => $type, 'id' => $model->id]) }}" method="POST" enctype="multipart/form-data">
        <x-adminlte-card title="{{ __('general_content.new_mail_trans_key') }}" theme="primary" maximizable> 
            @csrf
                <div class="form-group">
                    <input type="email" name="to" class="form-control" placeholder="" Value="{{ $contactMail }}"required>
                </div>
                <div class="form-group">
                    <input type="text" name="subject" class="form-control" placeholder="{{ __('general_content.object_trans_key') }} :" value="{{ $object }}" required>
                </div>
                <div class="form-group">
                    @php
                    $config = [
                        "height" => "200",
                        "toolbar" => [
                            // [groupName, [list of button]]
                            ['style', ['bold', 'italic', 'underline', 'clear']],
                            ['font', ['strikethrough', 'superscript', 'subscript']],
                            ['fontsize', ['fontsize']],
                            ['color', ['color']],
                            ['para', ['ul', 'ol', 'paragraph']],
                            ['height', ['height']],
                            ['table', ['table']],
                            ['insert', ['link', 'picture', 'video']],
                            ['view', ['fullscreen', 'codeview', 'help']],
                        ],
                    ]
                    @endphp
                    <x-adminlte-text-editor name="message" label="{{ __('general_content.message_trans_key') }}" label-class="text-primary"
                        igroup-size="sm" placeholder="..." :config="$config"> {!! $emailTemplate->content ?? '' !!}
                    </x-adminlte-text-editor>
                </div>
                <div class="form-group">

                    <label for="attachment">{{ __('general_content.attachment_trans_key') }}</label>
                    <div class="input-group">
                        <div class="input-group-prepend">
                            <span class="input-group-text"><i class="far fa-file"></i></span>
                        </div>
                        <div class="custom-file">
                            <input type="file" name="attachment" class="custom-file-input" id="chooseFile">
                            <label class="custom-file-label" for="chooseFile">{{ __('general_content.choose_file_trans_key') }}</label>
                        </div>
                    </div>
                </div>
            <div class="card-footer">
                <a href="{{ url()->previous() }}" class="btn btn-secondary"><i class="fas fa-arrow-left"></i> {{ __('general_content.back_trans_key') }}</a><button type="submit" class="btn btn-primary m-4"><i class="fas fa-envelope"></i>{{ __('general_content.to_submit_trans_key') }}</button> 
            </div>
        </x-adminlte-card>
    </form>
</div>

@stop

@section('css')
@stop

@section('js')
@stop