<?php

namespace App\Livewire;

use Carbon\Carbon;
use App\Models\User;
use Livewire\Component;
use Illuminate\Support\Str;
use Livewire\WithPagination;
use App\Models\Companies\Companies;
use App\Models\Workflow\Opportunities;
use App\Models\Companies\CompaniesContacts;
use App\Models\Companies\CompaniesAddresses;

class OpportunitiesIndex extends Component
{
    use WithPagination;
    protected $paginationTheme = 'bootstrap';
    protected $listeners = ['changeView'];

    public $viewType = 'table'; // Defaults to 'table'

    public $search = '';
    public $sortField = 'created_at'; // default sorting field
    public $sortAsc = false; // default sort direction
    public $searchIdStatus = '';
    
    public $userSelect = [];
    
    public $companies_id; 
    public $companies_contacts_id;   
    public $companies_addresses_id;  
    public $leads_id;  
    public $user_id; 
    public $label; 
    public $budget = '0';  
    public $close_date; 
    public $statu = '1'; 
    public $probality = '50'; 
    public $comment;

    public $idCompanie = '';
    public $statuses;

    // Validation Rules
    protected $rules = [
        'companies_id'=>'required',
        'companies_contacts_id'=>'required',
        'companies_addresses_id'=>'required',
        'label'=>'required',
        'user_id'=>'required',
        'budget'=>'required',
        'probality'=>'required',
    ];

    public function sortBy($field)
    {
        if ($this->sortField === $field) {
            $this->sortAsc = !$this->sortAsc; 
        } else {
            $this->sortAsc = true; 
        }
        $this->sortField = $field;
    }

    public function changeView($view)
    {
        $this->viewType = $view;
        session()->put('viewType', $view);
    }

    public function updatingSearch()
    {
        $this->resetPage();
    }
    
    public function mount()
    {
        $this->userSelect = User::select('id', 'name')->get();
       // Retrieve statuses and opportunities
        $this->statuses = [
            [
                'id' => 1, 
                'title' => __('general_content.new_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])  
                                                ->where('statu', 1)
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 2, 
                'title' => __('general_content.quote_made_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])
                                                ->where('statu', 2)
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 3, 
                'title' => __('general_content.negotiation_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])
                                                ->where('statu', 3)
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 4, 
                'title' => __('general_content.closed_won_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])
                                                ->where('statu', 4)
                                                ->where('updated_at', '>=', Carbon::now()->subHours(48))
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 5, 
                'title' => __('general_content.closed_lost_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])
                                                ->where('statu', 5)
                                                ->where('updated_at', '>=', Carbon::now()->subHours(48))
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 6, 
                'title' => __('general_content.informational_trans_key'), 
                'Opportunities' => Opportunities::with(['companie', 'contact'])
                                                ->where('statu', 6)
                                                ->where('updated_at', '>=', Carbon::now()->subHours(48))
                                                ->get()  // Keep Eloquent objects, no `toArray()`
            ]
        ];

        $this->viewType = session()->get('viewType', 'table'); 
    }

    public function render()
    {
        if(is_numeric($this->idCompanie)){
            $Opportunities = Opportunities::where('companies_id', $this->idCompanie)
                                            ->where('statu', 'like', '%'.$this->searchIdStatus.'%')
                                            ->orderBy($this->sortField, $this->sortAsc ? 'asc' : 'desc')
                                            ->paginate(15);
        }
        else{
            $Opportunities = Opportunities::where('label','like', '%'.$this->search.'%')
                                            ->where('statu', 'like', '%'.$this->searchIdStatus.'%')
                                            ->orderBy($this->sortField, $this->sortAsc ? 'asc' : 'desc')
                                            ->paginate(15);
        }

        $CompanieSelect = Companies::select('id', 'code','client_type','civility','label','last_name')->where('active', 1)->get();
        $AddressSelect = CompaniesAddresses::select('id', 'label','adress')->where('companies_id', $this->companies_id)->get();
        $ContactSelect = CompaniesContacts::select('id', 'first_name','name')->where('companies_id', $this->companies_id)->get();
        $userSelect = User::all();

        return view('livewire.opportunities-index')->with([
            'Opportunities' => $Opportunities,
            'CompanieSelect' => $CompanieSelect,
            'AddressSelect' => $AddressSelect,
            'ContactSelect' => $ContactSelect,
            'userSelect' => $userSelect,
        ]);
    }

    public function storeOpportunity(){
        $this->validate();

        // Create opportunity
        $OpportunityCreated = Opportunities::create([
                        'uuid'=> Str::uuid(),
                        'companies_id'=>$this->companies_id,  
                        'companies_contacts_id'=>$this->companies_contacts_id,    
                        'companies_addresses_id'=>$this->companies_addresses_id,   
                        'user_id'=>$this->user_id,   
                        'label'=>$this->label,   
                        'budget'=>$this->budget,   
                        'probality'=>$this->probality, 
                        'comment'=>$this->comment, 
        ]);
        
        return redirect()->route('opportunities.show', ['id' => $OpportunityCreated->id])->with('success', 'Successfully created new opportunity');
    }

    public function updateColumnOrder($order)
    {
        foreach ($order as $item) {
            // Update the order of the columns (statuses) if necessary
            //Opportunities::find($item['value'])->update(['statu_order' => $item['order']]);
        }

        $this->mount(); // Reload data after update
    }

    public function updateTaskOrder($groupOrder)
    {
        foreach ($groupOrder as $group) {
            foreach ($group['items'] as $item) {
                Opportunities::find($item['value'])->update(['statu' => $group['value']]);
            }
        }

        $this->mount(); // Reload data after update
    }

}
