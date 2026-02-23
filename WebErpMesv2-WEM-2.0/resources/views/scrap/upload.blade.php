@extends('adminlte::page')

@section('title', 'Upload Scrap CSV')

@section('content_header')
<div class="row mb-2">
    <div class="col-sm-6">
        <h1><i class="fas fa-file-csv text-info"></i> Upload Scrap CSV</h1>
    </div>
    <div class="col-sm-6">
        <ol class="breadcrumb float-sm-right">
            <li class="breadcrumb-item"><a href="{{ route('scrap.index') }}">Scrap Inventory</a></li>
            <li class="breadcrumb-item active">Upload CSV</li>
        </ol>
    </div>
</div>
@stop

@section('content')
<div class="row">
    <div class="col-md-8">
        <div class="card card-info">
            <div class="card-header">
                <h3 class="card-title">Upload Scrap Data</h3>
            </div>
            <form method="POST" action="{{ route('scrap.upload') }}" enctype="multipart/form-data">
                @csrf
                <div class="card-body">
                    @if($errors->any())
                        <div class="alert alert-danger">
                            <ul class="mb-0">
                                @foreach($errors->all() as $error)
                                    <li>{{ $error }}</li>
                                @endforeach
                            </ul>
                        </div>
                    @endif

                    @if(session('success'))
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle"></i> {{ session('success') }}
                        </div>
                    @endif

                    <div class="form-group">
                        <label>Select CSV File <span class="text-danger">*</span></label>
                        <div class="custom-file">
                            <input type="file" name="file" class="custom-file-input" id="csvFile" 
                                   accept=".csv,.xlsx,.xls" required>
                            <label class="custom-file-label" for="csvFile">Choose file...</label>
                        </div>
                        <small class="text-muted">Supported formats: CSV, XLSX, XLS (max 10MB)</small>
                    </div>

                    <div class="form-group">
                        <label>Default Values (optional)</label>
                        <div class="row">
                            <div class="col-md-6">
                                <select name="default_reason" class="form-control">
                                    <option value="">-- Default Reason Code --</option>
                                    @foreach(config('steel.scrap.reason_codes', ['cutting_waste' => 'Cutting Waste', 'defect' => 'Manufacturing Defect', 'damage' => 'Handling Damage', 'overrun' => 'Production Overrun', 'leftover' => 'Leftover Material']) as $code => $label)
                                        <option value="{{ $code }}">{{ $label }}</option>
                                    @endforeach
                                </select>
                            </div>
                            <div class="col-md-6">
                                <select name="default_stage" class="form-control">
                                    <option value="">-- Default Stage --</option>
                                    @foreach(config('steel.production_stages', ['fabrication' => ['name' => 'Fabrication'], 'painting' => ['name' => 'Painting'], 'dispatch' => ['name' => 'Ready for Dispatch']]) as $stage => $info)
                                        <option value="{{ $stage }}">{{ is_array($info) ? $info['name'] : $info }}</option>
                                    @endforeach
                                </select>
                            </div>
                        </div>
                        <small class="text-muted">Applied when CSV row doesn't have these values</small>
                    </div>

                    <div class="form-check">
                        <input type="checkbox" name="skip_header" class="form-check-input" id="skipHeader" checked>
                        <label class="form-check-label" for="skipHeader">Skip first row (header)</label>
                    </div>
                </div>
                <div class="card-footer">
                    <button type="submit" class="btn btn-info">
                        <i class="fas fa-upload"></i> Upload & Import
                    </button>
                    <a href="{{ route('scrap.index') }}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> Back
                    </a>
                </div>
            </form>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card card-outline card-secondary">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-info-circle"></i> CSV Format Guide</h3>
            </div>
            <div class="card-body">
                <p>Your CSV should have the following columns:</p>
                <table class="table table-sm table-bordered">
                    <thead class="thead-light">
                        <tr>
                            <th>Column</th>
                            <th>Required</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>material_name</code></td>
                            <td><span class="badge badge-danger">Yes</span></td>
                        </tr>
                        <tr>
                            <td><code>weight_kg</code></td>
                            <td><span class="badge badge-danger">Yes</span></td>
                        </tr>
                        <tr>
                            <td><code>quantity</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>length_mm</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>width_mm</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>thickness_mm</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>dimensions</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>reason_code</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>stage</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>location</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                        <tr>
                            <td><code>notes</code></td>
                            <td><span class="badge badge-secondary">No</span></td>
                        </tr>
                    </tbody>
                </table>

                <hr>
                <h6>Reason Codes:</h6>
                <ul class="list-unstyled small">
                    @foreach(config('steel.scrap.reason_codes', ['cutting_waste' => 'Cutting Waste', 'defect' => 'Manufacturing Defect', 'damage' => 'Handling Damage', 'overrun' => 'Production Overrun', 'leftover' => 'Leftover Material']) as $code => $label)
                        <li><code>{{ $code }}</code> - {{ $label }}</li>
                    @endforeach
                </ul>

                <hr>
                <h6>Production Stages:</h6>
                <ul class="list-unstyled small">
                    @foreach(config('steel.production_stages', ['fabrication' => ['name' => 'Fabrication'], 'painting' => ['name' => 'Painting'], 'dispatch' => ['name' => 'Ready for Dispatch']]) as $stage => $info)
                        <li><code>{{ $stage }}</code> - {{ is_array($info) ? $info['name'] : $info }}</li>
                    @endforeach
                </ul>
            </div>
            <div class="card-footer">
                <a href="#" class="btn btn-sm btn-outline-info" id="downloadTemplate">
                    <i class="fas fa-download"></i> Download Template
                </a>
            </div>
        </div>
    </div>
</div>
@stop

@section('js')
<script>
    // Show filename when file is selected
    $('.custom-file-input').on('change', function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).siblings('.custom-file-label').addClass('selected').html(fileName);
    });

    // Download template CSV
    $('#downloadTemplate').click(function(e) {
        e.preventDefault();
        var headers = ['material_name', 'weight_kg', 'quantity', 'length_mm', 'width_mm', 'thickness_mm', 'dimensions', 'reason_code', 'stage', 'location', 'notes'];
        var example = ['MS Plate', '15.5', '1', '500', '300', '10', '', 'cutting_waste', 'fabrication', 'Bay A', 'Sample entry'];
        
        var csv = headers.join(',') + '\n' + example.join(',');
        var blob = new Blob([csv], { type: 'text/csv' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'scrap_upload_template.csv';
        a.click();
    });
</script>
@stop
