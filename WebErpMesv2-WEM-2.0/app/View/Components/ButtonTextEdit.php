<?php

namespace App\View\Components;

use Illuminate\View\Component;

class ButtonTextEdit extends Component
{
    public $route;
    public $modalTarget;

    /**
     * Create a new component instance.
     *
     * @param  string  $route
     * @param  string|null  $modalTarget
     * @return void
     */
    public function __construct( $route = null, $modalTarget = null)
    {
        $this->route = $route;
        $this->modalTarget = $modalTarget;
    }

    /**
     * Get the view / contents that represent the component.
     *
     * @return \Illuminate\Contracts\View\View|\Closure|string
     */
    public function render()
    {
        return view('components.button-text-edit');
    }
}
