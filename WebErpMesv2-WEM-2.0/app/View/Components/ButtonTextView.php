<?php

namespace App\View\Components;

use Illuminate\View\Component;

class ButtonTextView extends Component
{
    public $route;
    public $downloadFile;
    public $modalTarget;
    public $bankFile;
    
    /**
     * Create a new component instance.
     *
     * @param  string  $route
     * @param  string|null  $downloadFile
     * @param  string|null  $modalTarget
     * @param  string|null  $bankFile
     * @return void
     */
    public function __construct( $route = null, $downloadFile = null, $modalTarget = null, $bankFile = null)
    {
        $this->route = $route;
        $this->downloadFile = $downloadFile;
        $this->modalTarget = $modalTarget;
        $this->bankFile = $bankFile;
    }

    /**
     * Get the view / contents that represent the component.
     *
     * @return \Illuminate\Contracts\View\View|\Closure|string
     */
    public function render()
    {
        return view('components.button-text-view');
    }
}
