self.onInit = function() {
    // Анхны эхлүүлэлт
};

self.onDataUpdated = function() {
    if (self.ctx.data && self.ctx.data.length > 0) {
        
        for (var i = 0; i < self.ctx.data.length; i++) {
            var datasourceData = self.ctx.data[i];
            
            if (datasourceData.dataKey && datasourceData.dataKey.name) {
                var dataKey = datasourceData.dataKey.name;
                
                if (datasourceData.data && datasourceData.data.length > 0) {
                    var latestPoint = datasourceData.data[datasourceData.data.length - 1];
                    var rawValue = "";

                    // 1. Хэрэв массив байвал түүнийг текст рүү хөрвүүлнэ
                    if (Array.isArray(latestPoint)) {
                        rawValue = latestPoint.join(',');
                    } else if (latestPoint !== undefined && latestPoint !== null) {
                        rawValue = latestPoint.toString();
                    }

                    // 2. ТЕКСТИЙГ ХЭРЧИЖ БОДИТ УТГЫГ САНАМСАРГҮЙ БИШ, ЯГ ТАГ ШҮҮХ
                    if (rawValue.includes(',')) {
                        var parts = rawValue.split(',');
                        
                        for (var p = 0; p < parts.length; p++) {
                            var item = parts[p].trim();
                            
                            // Нөхцөл: Хоосон биш, тоо мөн, БӨГӨӨД 1000000000-аас бага (Timestamp биш) утгыг хайна
                            if (item !== "" && !isNaN(item)) {
                                var numCheck = Number(item);
                                if (numCheck < 1000000000) { 
                                    rawValue = item; // Эндээс яг 77.97 гэсэн утгыг барьж авна
                                    break;
                                }
                            }
                        }
                    }

                    // 3. Цэвэр тоо руу хөрвүүлж форматлах
                    var numericValue = Number(rawValue);
                    var formattedValue = '--';
                    console.log(numericValue)
                    if (!isNaN(numericValue) && rawValue !== "") {
                        var decimals = datasourceData.dataKey.decimals !== undefined ? datasourceData.dataKey.decimals : 1;
                        var units = datasourceData.dataKey.units ? ' ' + datasourceData.dataKey.units : '';
                        formattedValue = numericValue.toFixed(decimals) + units;
                    } else if (rawValue !== undefined && rawValue !== null) {
                        formattedValue = rawValue.toString();
                    }
                    
                    // 4. HTML дээрх харгалзах ID руу утгыг шахах
                    var element = self.ctx.$container.find('#' + dataKey);
                    if (element && element.length > 0) {
                        element.text(formattedValue);
                    }
                }
            }
        }
    }
};

/* Сүүлийн хувилбарын олон дата хүлээж авах тохиргоо */
self.typeParameters = function() {
    return {
        maxDatasources: 1,
        maxDataKeys: 10,
        singleEntity: true
    };
};

self.onDestroy = function() {
};
