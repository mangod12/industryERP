<?php

namespace App\Livewire;

use Carbon\Carbon;
use App\Models\User;
use Livewire\Component;
use Livewire\WithPagination;
use App\Models\Workflow\Leads;
use App\Models\Companies\Companies;
use App\Models\Companies\CompaniesContacts;
use App\Models\Companies\CompaniesAddresses;

class LeadsIndex extends Component
{
    use WithPagination;
    protected $paginationTheme = 'bootstrap';

    public $viewType = 'table'; // Defaults to 'table'

    public $search = '';
    public $sortField = 'statu'; // default sorting field
    public $sortAsc = true; // default sort direction
    
    public $searchIdPriority = '';
    public $userSelect = [];
    private $Leadslist;
    
    public $id;
    public $companies_id='';
    public $companies_contacts_id;   
    public $companies_addresses_id; 
    public $user_id;
    public $source;
    public $priority = 3;
    public $campaign;
    public $comment;

    public $idCompanie = '';
    public $statuses;

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

    // Validation Rules
    protected $rules = [
        'companies_id'=>'required',
        'companies_contacts_id'=>'required',
        'companies_addresses_id'=>'required',
        'user_id'=>'required',
        'source'=>'required',
        'priority'=>'required',
    ];

    public function mount()
    {

        $this->userSelect = User::select('id', 'name')->get();
        // Retrieve statuses and Leads
        $this->statuses = [
            [
                'id' => 1, 
                'title' => __('general_content.new_trans_key'), 
                'Leads' => Leads::with(['companie', 'contact'])
                                ->where('statu', 1)
                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 2, 
                'title' => __('general_content.assigned_trans_key'), 
                'Leads' => Leads::with(['companie', 'contact'])
                                ->where('statu', 2)
                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 3, 
                'title' => __('general_content.in_progress_trans_key'), 
                'Leads' => Leads::with(['companie', 'contact'])
                                ->where('statu', 3)
                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 4, 
                'title' => __('general_content.converted_trans_key'), 
                'Leads' => Leads::with(['companie', 'contact'])
                                ->where('statu', 4)
                                ->where('updated_at', '>=', Carbon::now()->subHours(48))
                                ->get()  // Keep Eloquent objects, no `toArray()`
            ],
            [
                'id' => 5, 
                'title' => __('general_content.lost_trans_key'), 
                'Leads' => Leads::with(['companie', 'contact'])
                                ->where('statu', 5)
                                ->where('updated_at', '>=', Carbon::now()->subHours(48))
                                ->get()  // Keep Eloquent objects, no `toArray()`
            ]
        ];

        $this->viewType = session()->get('viewType', 'table'); 
    }

    public function render()
    {
        if(is_numeric($this->idCompanie)){
            $Leadslist = $this->Leadslist = Leads::where('companies_id', $this->idCompanie)
                                                ->orderBy($this->sortField, $this->sortAsc ? 'asc' : 'desc')
                                                ->paginate(15);
        }
        else{
            $Leadslist = $this->Leadslist = Leads::where('campaign','like', '%'.$this->search.'%')
                                                ->where('priority', 'like', '%'.$this->searchIdPriority.'%')
                                                ->orderBy($this->sortField, $this->sortAsc ? 'asc' : 'desc')
                                                ->paginate(15);
        }
        
        $CompanieSelect = Companies::select('id', 'code','client_type','civility','label','last_name')->where('active', 1)->get();
        $AddressSelect = CompaniesAddresses::select('id', 'label','adress')->where('companies_id',  $this->companies_id)->get();
        $ContactSelect = CompaniesContacts::select('id', 'first_name','name')->where('companies_id', $this->companies_id)->get();
        $userSelect = User::all();

        return view('livewire.leads-index', [
            'Leadslist' => $Leadslist,
            'CompanieSelect' => $CompanieSelect,
            'AddressSelect' => $AddressSelect,
            'ContactSelect' => $ContactSelect,
            'userSelect' => $userSelect,
        ]);

    }

    public function storeLead(){
        $this->validate();

        // Create lead
        Leads::create([
                        'companies_id'=>$this->companies_id,  
                        'companies_contacts_id'=>$this->companies_contacts_id,    
                        'companies_addresses_id'=>$this->companies_addresses_id,   
                        'user_id'=>$this->user_id,   
                        'source'=>$this->source,   
                        'priority'=>$this->priority,   
                        'campaign'=>$this->campaign, 
                        'comment'=>$this->comment, 
        ]);
        
        return redirect()->route('leads')->with('success', 'New lead add successfully');
    }

    public function updateColumnOrder($order)
    {
        foreach ($order as $item) {
            // Update the order of the columns (statuses) if necessary
            //Leads::find($item['value'])->update(['statu_order' => $item['order']]);
        }

        $this->mount(); // Reload data after update
    }

    public function updateTaskOrder($groupOrder)
    {
        foreach ($groupOrder as $group) {
            foreach ($group['items'] as $item) {
                Leads::find($item['value'])->update(['statu' => $group['value']]);
            }
        }

        $this->mount(); // Reload data after update
    }
}
