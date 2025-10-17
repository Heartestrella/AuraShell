function compressContext(aiChatApiOptionsBody, messagesHistory) {
  return new Promise(async (resolve) => {
    try {
      var compressedCount = 0;
      var lastMcpIndex = -1;
      for (var i = aiChatApiOptionsBody.messages.length - 1; i >= 0; i--) {
        var msg = aiChatApiOptionsBody.messages[i];
        if (msg.role === 'user' && Array.isArray(msg.content) && msg.content.length >= 2) {
          var firstPart = msg.content[0];
          if (firstPart.type === 'text' && firstPart.text && firstPart.text.indexOf('[') === 0 && firstPart.text.indexOf('->') > -1 && firstPart.text.indexOf('] 执行结果:') > -1) {
            lastMcpIndex = i;
            break;
          }
        }
      }
      var mcpIndicesToCompress = [];
      for (var i = 0; i < aiChatApiOptionsBody.messages.length; i++) {
        var msg = aiChatApiOptionsBody.messages[i];
        if (msg.role === 'user' && Array.isArray(msg.content) && msg.content.length >= 2) {
          var firstPart = msg.content[0];
          if (firstPart.type === 'text' && firstPart.text && firstPart.text.indexOf('[') === 0 && firstPart.text.indexOf('->') > -1 && firstPart.text.indexOf('] 执行结果:') > -1) {
            if (i !== lastMcpIndex) {
              mcpIndicesToCompress.push(i);
            }
          }
        }
      }
      var newMessages = [];
      for (var i = 0; i < aiChatApiOptionsBody.messages.length; i++) {
        var msg = aiChatApiOptionsBody.messages[i];
        var shouldSkip = false;
        if (msg.role === 'assistant' && typeof msg.content === 'string') {
          for (var j = 0; j < mcpIndicesToCompress.length; j++) {
            if (i === mcpIndicesToCompress[j] - 1) {
              if (msg.content.indexOf('<use_mcp_tool>') > -1 || msg.content.indexOf('use_mcp_tool') > -1) {
                var cleanedContent = msg.content;
                var useToolStart = cleanedContent.indexOf('<use_mcp_tool>');
                var useToolEnd = cleanedContent.indexOf('</use_mcp_tool>');
                if (useToolStart > -1 && useToolEnd > -1) {
                  cleanedContent = cleanedContent.substring(0, useToolStart) + cleanedContent.substring(useToolEnd + 15);
                  cleanedContent = cleanedContent.trim();
                  if (cleanedContent.length > 0) {
                    newMessages.push({
                      role: msg.role,
                      content: cleanedContent,
                    });
                  } else {
                    shouldSkip = true;
                  }
                } else {
                  newMessages.push(msg);
                }
                break;
              }
            }
          }
          if (!shouldSkip && newMessages.length === i) {
            newMessages.push(msg);
          }
        } else if (mcpIndicesToCompress.indexOf(i) > -1) {
          compressedCount++;
          var firstPart = msg.content[0];
          var newContent = [];
          newContent.push(firstPart);
          newContent.push({
            type: 'text',
            text: '*',
          });
          for (var j = 2; j < msg.content.length; j++) {
            newContent.push(msg.content[j]);
          }
          newMessages.push({
            role: msg.role,
            content: newContent,
          });
        } else {
          newMessages.push(msg);
        }
      }
      var lastMcpHistoryIndex = -1;
      for (var i = messagesHistory.length - 1; i >= 0; i--) {
        var item = messagesHistory[i];
        if (item.isMcp && item.messages.role === 'user' && Array.isArray(item.messages.content) && item.messages.content.length >= 2) {
          var firstPart = item.messages.content[0];
          if (firstPart.type === 'text' && firstPart.text && firstPart.text.indexOf('[') === 0 && firstPart.text.indexOf('->') > -1 && firstPart.text.indexOf('] 执行结果:') > -1) {
            lastMcpHistoryIndex = i;
            break;
          }
        }
      }
      var mcpHistoryIndicesToCompress = [];
      for (var i = 0; i < messagesHistory.length; i++) {
        var item = messagesHistory[i];
        if (item.isMcp && item.messages.role === 'user' && Array.isArray(item.messages.content) && item.messages.content.length >= 2) {
          var firstPart = item.messages.content[0];
          if (firstPart.type === 'text' && firstPart.text && firstPart.text.indexOf('[') === 0 && firstPart.text.indexOf('->') > -1 && firstPart.text.indexOf('] 执行结果:') > -1) {
            if (i !== lastMcpHistoryIndex) {
              mcpHistoryIndicesToCompress.push(i);
            }
          }
        }
      }
      var newHistory = [];
      for (var i = 0; i < messagesHistory.length; i++) {
        var item = messagesHistory[i];
        var shouldSkipHistory = false;
        if (!item.isMcp && item.messages.role === 'assistant' && typeof item.messages.content === 'string') {
          for (var j = 0; j < mcpHistoryIndicesToCompress.length; j++) {
            if (i === mcpHistoryIndicesToCompress[j] - 1) {
              if (item.messages.content.indexOf('<use_mcp_tool>') > -1 || item.messages.content.indexOf('use_mcp_tool') > -1) {
                var cleanedContent = item.messages.content;
                var useToolStart = cleanedContent.indexOf('<use_mcp_tool>');
                var useToolEnd = cleanedContent.indexOf('</use_mcp_tool>');
                if (useToolStart > -1 && useToolEnd > -1) {
                  cleanedContent = cleanedContent.substring(0, useToolStart) + cleanedContent.substring(useToolEnd + 15);
                  cleanedContent = cleanedContent.trim();
                  if (cleanedContent.length > 0) {
                    newHistory.push({
                      messages: {
                        role: item.messages.role,
                        content: cleanedContent,
                      },
                      isMcp: item.isMcp,
                    });
                  } else {
                    shouldSkipHistory = true;
                  }
                } else {
                  newHistory.push(item);
                }
                break;
              }
            }
          }
          if (!shouldSkipHistory && newHistory.length === i) {
            newHistory.push(item);
          }
        } else if (mcpHistoryIndicesToCompress.indexOf(i) > -1) {
          var firstPart = item.messages.content[0];
          var newContent = [];
          newContent.push(firstPart);
          newContent.push({
            type: 'text',
            text: '*',
          });
          for (var j = 2; j < item.messages.content.length; j++) {
            newContent.push(item.messages.content[j]);
          }
          newHistory.push({
            messages: {
              role: item.messages.role,
              content: newContent,
            },
            isMcp: item.isMcp,
          });
        } else {
          newHistory.push(item);
        }
      }
      console.log('压缩完成');
      console.log('已压缩', compressedCount, '个MCP工具执行结果');
      resolve({
        aiChatApiOptionsBody: {
          model: aiChatApiOptionsBody.model,
          temperature: aiChatApiOptionsBody.temperature,
          messages: newMessages,
          stream: aiChatApiOptionsBody.stream,
          stream_options: aiChatApiOptionsBody.stream_options,
        },
        messagesHistory: newHistory,
      });
    } catch (error) {
      console.error('压缩上下文时出错:', error);
      debugger;
      throw error;
    }
  });
}
