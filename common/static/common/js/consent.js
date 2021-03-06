"use strict";

function submitConsent(e, d) {
	$.post('/consent_accept', {
		'consent': 'true'
	},
	function(res) {
		if (res.res === 'success') {
			window.location.replace('/getting_started');
		} else {
			location.reload();
		}
	});
	return false;
}

$(function() {
    $("#confirmation").on("click", submitConsent);
});
