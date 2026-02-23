<?php

namespace App\Livewire\ArrowSteps;

use App\Models\Purchases\PurchasesQuotation;
use Livewire\Component;

class ArrowRFQ extends Component
{
    public $RFQId;
    public $RFQStatu;

    public function mount($RFQId,  $RFQStatu) 
    {
        $this->RFQId = $RFQId;
        $this->RFQStatu = $RFQStatu;
    }

    public function render()
    {
        return view('livewire.arrow-steps.arrow-rfq');
    }

    public function changeStatu($statuNumber){
        try{
            PurchasesQuotation::where('id',$this->RFQId)->update(['statu'=>$statuNumber]);
            return redirect()->route('purchases.quotations.show', ['id' =>  $this->RFQId])->with('success', 'Successfully updated statu');
        }catch(\Exception $e){
            session()->flash('error',"Something goes wrong on update statu");
        }
    }
}
