import { Alert, TouchableOpacity, View,Text } from 'react-native'
import React, { useEffect, useRef, useState } from 'react'
import { StatusBar } from 'expo-status-bar'
import MessageList  from '@/components/MessageList'
import {MessageInterface} from '@/types/types';
import { widthPercentageToDP as wp, heightPercentageToDP as hp } from 'react-native-responsive-screen'
import { GestureHandlerRootView, TextInput } from 'react-native-gesture-handler'
import { Feather } from '@expo/vector-icons'
import {callChatBotAPI } from '@/services/chatBot'
import PageHeader from '@/components/PageHeader'
import {  useCart } from '@/components/CartContext'

const ChatRoom = () => {
  const {addToCart, emptyCart} = useCart();

  const [messages, setMessages] = useState<MessageInterface[]>([]);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [isLongRequest, setIsLongRequest] = useState<boolean>(false);
  const textRef = useRef('')
  const inputRef = useRef<TextInput>(null)
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    return () => {
      // Cleanup timeout on unmount
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    }
  }, []);

  const handleSendMessage = async () => {
    let message = textRef.current.trim();
    if (!message) return;
    
    try {
        // Add the user message to the list of messages
        let InputMessages = [...messages, { content: message, role: 'user' }];
        setMessages(InputMessages);
        
        // Clear input
        textRef.current = ''
        if(inputRef) inputRef?.current?.clear();
        
        // Show typing indicator
        setIsTyping(true);
        
        // Set up long request indicator after 10 seconds
        timeoutRef.current = setTimeout(() => {
          setIsLongRequest(true);
        }, 10000);

        // Make API call
        let responseMessage = await callChatBotAPI(InputMessages);
        
        // Clear timeout and indicators
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        setIsTyping(false);
        setIsLongRequest(false);
        
        // Update messages with response
        setMessages(prevMessages => [...prevMessages, responseMessage]);
        
        // Handle cart updates if needed
        if (responseMessage?.memory?.order) {
            emptyCart();
            responseMessage.memory.order.forEach((item: any) => {
                addToCart(item.item, item.quantity);
            });
        }

    } catch(err: any) {
        // Clear indicators
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        setIsTyping(false);
        setIsLongRequest(false);
        
        // Show error message
        Alert.alert(
            'Error',
            err.message || 'Failed to get response. Please try again.',
            [{ text: 'OK' }]
        );
    }
  }

  return (
    <GestureHandlerRootView>
        <StatusBar style='dark' />
        
        <View
            className='flex-1 bg-white'
        >

        <PageHeader title="Chat Bot" showHeaderRight={false} bgColor='white'/>
        
        <View className='h-3 border-b border-neutral-300' />

        <View
            className='flex-1 justify-between bg-neutral-100 overflow-visibile'
        >
            <View className='flex-1'>
                <MessageList 
                    messages={messages}
                    isTyping={isTyping}
                />
                {isLongRequest && (
                    <View className="bg-yellow-100 p-2 mx-3 rounded-lg mt-2">
                        <Text className="text-yellow-800 text-sm">
                            This is taking longer than usual. Please wait...
                        </Text>
                    </View>
                )}
            </View>

            <View
                style={{marginBottom: hp(2.7)}}
                className='pt-2'
            >
                <View
                    className="flex-row mx-3 justify-between border p-2 bg-white border-neutral-300  rounded-full pl-5"
                >
                    <TextInput 
                        ref = {inputRef}
                        onChangeText={value => textRef.current = value}
                        placeholder='Type message...'
                        style={{fontSize: hp(2)}}
                        className='flex-1 mr2'
                    />
                    <TouchableOpacity
                        onPress = {handleSendMessage}
                        className='bg-neutral-200 p-2 mr-[1px] rounded-full'
                    >
                        <Feather name="send" size={hp(2.7)} color="#737373"/>
                    </TouchableOpacity>
                </View>
            </View>
        </View>



        </View>
    </GestureHandlerRootView>
  )
}

export default ChatRoom
