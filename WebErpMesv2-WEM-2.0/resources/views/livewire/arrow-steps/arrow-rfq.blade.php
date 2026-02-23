<div class="row ">
    <div class="col-12">
        <div class="arrow-steps clearfix">
            <div class="col-1 step {{ $RFQStatu == 1 ? 'current' : '' }} {{ $RFQStatu <= 1 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(1)">{{ __('general_content.in_progress_trans_key') }}</a></span> </div>
            <div class="col-2 step {{ $RFQStatu == 2 ? 'current' : '' }} {{ $RFQStatu <= 2 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(2)">{{ __('general_content.send_trans_key') }}</a></span> </div>
            <div class="col-2 step {{ $RFQStatu == 3 ? 'current' : '' }} {{ $RFQStatu <= 3 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(3)">{{ __('general_content.partly_received_trans_key') }}</a></span> </div>
            <div class="col-2 step {{ $RFQStatu == 4 ? 'current' : '' }} {{ $RFQStatu <= 4 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(4)">{{ __('general_content.rceived_trans_key') }}</a></span> </div>
            <div class="col-2 step {{ $RFQStatu == 5 ? 'current' : '' }} {{ $RFQStatu <= 5 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(5)">{{ __('general_content.po_partly_created_trans_key') }}</a></span> </div>
            <div class="col-2 step {{ $RFQStatu == 6 ? 'current' : '' }} {{ $RFQStatu <= 6 ? ' ' : 'done' }}"> <span><a href="#" wire:click="changeStatu(6)">{{ __('general_content.po_created_trans_key') }}</a></span> </div></div>
    </div>
</div>



