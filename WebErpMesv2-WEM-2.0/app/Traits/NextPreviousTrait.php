<?php
namespace App\Traits;

use Illuminate\Database\Eloquent\Model;

trait NextPreviousTrait {
    /**
     * Get the URLs for the next and previous records based on the given model and ID.
     *
     * @param Model $model The Eloquent model instance.
     * @param int $id The current record ID.
     * @return array An array containing the URLs for the previous and next records.
     *               The first element is the previous record URL, and the second element is the next record URL.
     *               If there is no previous or next record, the respective URL will be null.
     */
    public function getNextPrevious(Model $model, $id) {
        $previousId = $model::where('id', '<', $id)->orderBy('id', 'desc')->first();
        $nextId = $model::where('id', '>', $id)->orderBy('id', 'asc')->first();
        $routeName = str_replace('_', '.', $model->getTable());
        $previousUrl = $previousId ? route("{$routeName}.show", ['id' => $previousId]) : null;
        $nextUrl = $nextId ? route("{$routeName}.show", ['id' => $nextId]) : null;

        return [$previousUrl, $nextUrl];
    }
}
