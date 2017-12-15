function loader()
{
	$("#jumbo").hide();
	$("#calulating").show();
	var i = 100;
	var timer = 50;
	var counterBack = setInterval(function(){
			i--;
		if(i>0){
			$('.progress-bar').css('width', (100-i)+'%');
			$('.progress-bar').text((100-i)+'%');
		} else {
			clearTimeout(counterBack);
		}
	}, timer);
}
function showValue(newValue)
{
	document.getElementById("range").innerHTML=newValue;
}