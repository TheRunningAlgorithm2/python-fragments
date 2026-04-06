<>
    <div classes="flex flex-col gap-3">
        <div for={{ item in user.items }} classes="p-3 rounded-lg bg-gray-800">
            <p style={{ {"color": "red"} }}>{{ item.name }}</p>
            <p if={{ item.description }}>{{ item.description }}</p>
            <p > This is an item</p>
            <  input />
        </div>
    </div>
</>