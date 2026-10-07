function removeItem(id) {
  $.post('main.php?module=Items&action=deleteItem', {id: id});
}
function archiveItem() {
  $http.post('services.php', {module: 'Items', action: 'archiveItem'});
}
function missing() {
  $.post('main.php?module=Items&action=nope', {});
}
function noRoute() {
  $.post('health.php', {});
}
